"""Post-process existing recommendation reports to add LLM explanations.

Reads JSON files produced by matching_engine.recommend (without or with
explanations) and writes new files that include an explanation paragraph
generated from structured overlaps.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from common.config import settings
from . import matching_engine as me


def _load_json(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _tag_set(profile: Dict, key: str) -> Set[str]:
    items = profile.get("canonical_tags", {}).get(key, [])
    return {d.get("tag") for d in items if isinstance(d, dict) and d.get("tag")}


def _resolve_profile(path_str: str, default_dir: Path) -> Optional[Path]:
    p = Path(path_str)
    if p.exists():
        return p
    p2 = default_dir / path_str
    return p2 if p2.exists() else None


def _generate_for_item(org: Dict, grant: Dict) -> Optional[Dict]:

    o = {
        "mission_tags": _tag_set(org, "mission_tags"),
        "population_tags": _tag_set(org, "population_tags"),
        "org_type_tags": _tag_set(org, "org_type_tags"),
        "geography_tags": _tag_set(org, "geography_tags"),
        "red_flag_tags": _tag_set(org, "red_flag_tags"),
    }
    g = {
        "mission_tags": _tag_set(grant, "mission_tags"),
        "population_tags": _tag_set(grant, "population_tags"),
        "org_type_tags": _tag_set(grant, "org_type_tags"),
        "geography_tags": _tag_set(grant, "geography_tags"),
        "red_flag_tags": _tag_set(grant, "red_flag_tags"),
    }
    overlap = {
        "mission": sorted(o["mission_tags"] & g["mission_tags"]) if o["mission_tags"] else [],
        "population": sorted(o["population_tags"] & g["population_tags"]) if o["population_tags"] else [],
        "org_type": sorted(o["org_type_tags"] & g["org_type_tags"]) if o["org_type_tags"] else [],
        "geography": sorted(o["geography_tags"] & g["geography_tags"]) if o["geography_tags"] else [],
    }
    return me._generate_explanation(org, grant, overlap)


def _score_for_item(org: Dict, grant: Dict) -> float:
    try:
        score, _bucket, _reasons = me._score_and_reasons(org, grant)
        return float(score)
    except Exception:
        return 0.0


def _ensure_base_fields(org: Dict, grant: Dict, item: Dict) -> None:
    # Compute score, bucket, reasons using engine
    try:
        score, bucket, reasons = me._score_and_reasons(org, grant)
    except Exception:
        score, bucket, reasons = 0.0, item.get("bucket") or "Avoid", item.get("reasons") or []
    item["score"] = float(score)
    item["bucket"] = bucket
    item["reasons"] = reasons
    # Deadlines and funding from grant
    dl = grant.get("deadline", {}) if isinstance(grant, dict) else {}
    # Derive rolling from source text if extractor missed 'anytime' style phrasing
    try:
        dl_status = dl.get("status") if isinstance(dl, dict) else None
        if (not dl_status or dl_status == "unspecified") and me._rolling_from_source(grant):
            dl = {**dl, "status": "rolling"}
    except Exception:
        pass
    # Keep only the closest deadline (normalized single date)
    try:
        dates = (dl.get("dates") or []) if isinstance(dl, dict) else []
        # Compute closest upcoming or latest past
        from datetime import date as _date
        parsed = []
        for s in dates:
            try:
                y, m, d = s.split("-")
                parsed.append(_date(int(y), int(m), int(d)))
            except Exception:
                continue
        if parsed:
            today = _date.today()
            future = [dt for dt in parsed if dt >= today]
            nd = min(future).isoformat() if future else max(parsed).isoformat()
        else:
            nd = None
        item["deadline"] = nd
    except Exception:
        item["deadline"] = None
    if item.get("deadline") is None:
        item["deadline_note"] = "Could not locate; please use the URL to double-check."
    # Ensure we do not keep the old fields
    item.pop("deadlines", None)
    item.pop("deadline_status", None)
    # Anticipated Funding Amount (verbatim)
    try:
        item["anticipated_funding_amount"] = me._extract_anticipated_from_source(grant)
    except Exception:
        item["anticipated_funding_amount"] = None
    # URL from source
    try:
        item["url"] = (grant.get("source") or {}).get("url")
    except Exception:
        item["url"] = None


def _extract_synopsis(grant: Dict) -> Optional[str]:
    try:
        return me._extract_synopsis_from_source(grant)
    except Exception:
        return None


def process_report_file(
    in_path: Path,
    orgs_dir: Path,
    grants_dir: Path,
    overwrite: bool = False,
    force: bool = False,
    suffix: str = "_explained",
) -> Optional[Path]:
    data = _load_json(in_path)
    org_name = data.get("org_profile")
    if not org_name:
        return None
    org_path = _resolve_profile(org_name, orgs_dir)
    if not org_path:
        return None
    org = _load_json(org_path)
    recs = data.get("recommendations", [])
    # Explanation gating parameters
    top_k = settings.EXPLAIN_TOP_K
    min_score = settings.EXPLAIN_MIN_SCORE

    new_recs: List[Dict] = []
    for idx, item in enumerate(recs):
        if not isinstance(item, dict):
            continue
        # Pass through errors as-is
        if item.get("error"):
            new_recs.append(item)
            continue
        # Decide whether to (re)generate explanation for this item
        score_val = item.get("score")
        gp = item.get("grant_profile")
        link_url = None
        gp_path = _resolve_profile(gp, grants_dir) if gp else None
        # Load grant if needed for link or missing score
        grant_loaded = None
        if gp_path:
            try:
                grant_loaded = _load_json(gp_path)
                link_url = (grant_loaded.get("source") or {}).get("url")
            except Exception:
                grant_loaded = None
                link_url = None
        # If score is missing, or item lacks full details (likely pruned earlier), recompute using engine
        if (score_val is None or "bucket" not in item) and grant_loaded is not None:
            score_val = _score_for_item(org, grant_loaded)
        if score_val is None:
            score_val = 0.0
        # Now compute gating with the best available score
        do_explain = (idx < top_k) or (score_val >= min_score)
        if item.get("explanation") and not force:
            # Already has explanation; keep only if within gating; otherwise prune
            if do_explain:
                # Ensure base fields are present
                if grant_loaded is not None:
                    _ensure_base_fields(org, grant_loaded, item)
                # Convert existing explanation to paragraph string if needed
                try:
                    exp_val = item.get("explanation")
                    para = None
                    if isinstance(exp_val, dict):
                        para = exp_val.get("paragraph")
                        if (not para) and isinstance(exp_val.get("bullets"), list):
                            para = " ".join([b.strip() for b in exp_val["bullets"] if isinstance(b, str)])
                    elif isinstance(exp_val, str):
                        para = exp_val
                    if para:
                        item["explanation"] = para
                except Exception:
                    # If conversion fails, drop explanation rather than breaking structure
                    item.pop("explanation", None)
                # Attach synopsis when gated
                if grant_loaded is not None:
                    syn = _extract_synopsis(grant_loaded)
                    if syn:
                        item["synopsis"] = syn
                new_recs.append(item)
            else:
                # Remove explanation and keep full base fields
                item.pop("explanation", None)
                item.pop("synopsis", None)
                if grant_loaded is not None:
                    _ensure_base_fields(org, grant_loaded, item)
                new_recs.append(item)
            continue
        if not gp:
            continue
        grant_path = _resolve_profile(gp, grants_dir)
        if not grant_path:
            continue
        grant = grant_loaded if grant_loaded is not None else _load_json(grant_path)
        # Ensure base fields for all outputs
        _ensure_base_fields(org, grant, item)
        if do_explain:
            exp = _generate_for_item(org, grant)
            if exp:
                # Keep only paragraph string in output
                para = None
                if isinstance(exp, dict):
                    para = exp.get("paragraph")
                    if (not para) and isinstance(exp.get("bullets"), list):
                        para = " ".join([b.strip() for b in exp["bullets"] if isinstance(b, str)])
                elif isinstance(exp, str):
                    para = exp
                if para:
                    item["explanation"] = para
            # Attach synopsis when gated
            syn = _extract_synopsis(grant)
            if syn:
                item["synopsis"] = syn
        else:
            # Explicitly ensure no explanation exists when outside gating
            item.pop("explanation", None)
            item.pop("synopsis", None)
        new_recs.append(item)
    # Replace recommendations with gated/pruned list
    data["recommendations"] = new_recs
    if overwrite:
        out_path = in_path
    else:
        b = in_path.stem
        out_path = in_path.with_name(f"{b}{suffix}{in_path.suffix}")
    _write_json(out_path, data)
    return out_path


def _iter_inputs(in_arg: Optional[str], in_dir: Optional[str]) -> Iterable[Path]:
    if in_arg:
        p = Path(in_arg)
        if p.is_file():
            yield p
    elif in_dir:
        d = Path(in_dir)
        for p in sorted(d.glob("*_recommendations.json")):
            yield p


def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Add LLM explanations to existing recommendation reports.")
    parser.add_argument("--in", dest="in_path", help="Path to a single report JSON.")
    parser.add_argument("--in-dir", dest="in_dir", help="Directory of report JSONs (pattern: *_recommendations.json).")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite input files in-place.")
    parser.add_argument("--force", action="store_true", help="Regenerate even if explanation already exists.")
    parser.add_argument("--suffix", default="_explained", help="Suffix for new files when not overwriting.")
    parser.add_argument("--org-dir", default=str(settings.PROCESSED_ORGS_DIR), help="Directory containing org profiles.")
    parser.add_argument("--grants-dir", default=str(settings.PROCESSED_GRANTS_DIR), help="Directory containing grant profiles.")
    args = parser.parse_args(argv)

    if not args.in_path and not args.in_dir:
        print("[error] Provide --in or --in-dir")
        return 2

    orgs_dir = Path(args.org_dir)
    grants_dir = Path(args.grants_dir)
    outputs: List[Path] = []
    for p in _iter_inputs(args.in_path, args.in_dir):
        out = process_report_file(p, orgs_dir, grants_dir, overwrite=args.overwrite, force=args.force, suffix=args.suffix)
        if out:
            print(f"[ok] wrote {out}")
            outputs.append(out)
        else:
            print(f"[warn] skipped {p}")
    return 0 if outputs else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
