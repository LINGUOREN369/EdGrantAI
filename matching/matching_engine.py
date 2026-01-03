"""Matching engine: rank grant profiles for a given organization profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple, Optional

from common.config import settings
from mapping.embedding_matcher import load_taxonomy_embeddings, cosine_similarity


def _load_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _generate_explanation(org: Dict, grant: Dict, overlap: Dict[str, List[str]]) -> Optional[Dict]:
    try:
        from openai import OpenAI
    except Exception:
        return None
    prompt = _load_text(settings.MATCHING_EXPLAINER_PROMPT_PATH)
    payload = {
        "org": {
            "id": org.get("org_id"),
            "mission_tags": sorted({d.get("tag") for d in org.get("canonical_tags", {}).get("mission_tags", []) if isinstance(d, dict) and d.get("tag")}),
            "population_tags": sorted({d.get("tag") for d in org.get("canonical_tags", {}).get("population_tags", []) if isinstance(d, dict) and d.get("tag")}),
            "org_type_tags": sorted({d.get("tag") for d in org.get("canonical_tags", {}).get("org_type_tags", []) if isinstance(d, dict) and d.get("tag")}),
            "geography_tags": sorted({d.get("tag") for d in org.get("canonical_tags", {}).get("geography_tags", []) if isinstance(d, dict) and d.get("tag")}),
        },
        "grant": {
            "id": grant.get("grant_id") or grant.get("source", {}).get("path"),
            "overlap": {
                "mission": overlap.get("mission", []),
                "population": overlap.get("population", []),
                "org_type": overlap.get("org_type", []),
                "geography": overlap.get("geography", []),
            },
            "red_flags": sorted({d.get("tag") for d in grant.get("canonical_tags", {}).get("red_flag_tags", []) if isinstance(d, dict) and d.get("tag")}),
            "deadline": grant.get("deadline", {}),
            "funding": grant.get("funding", {}),
        },
    }
    final_prompt = prompt + "\n\nINPUT:\n" + json.dumps(payload, indent=2)
    try:
        client = OpenAI()
        resp = client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[{"role": "user", "content": final_prompt}],
        )
        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            s = text.find("[") if "[" in text else text.find("{")
            e = text.rfind("]") if "]" in text else text.rfind("}")
            if s != -1 and e != -1:
                text = text[s : e + 1]
        data = json.loads(text)
        if not isinstance(data, dict):
            return None
        rec = data.get("recommendation")
        paragraph = data.get("paragraph") if isinstance(data.get("paragraph"), str) else None
        bullets = data.get("bullets") if isinstance(data.get("bullets"), list) else None
        # Prefer paragraph output; fall back to bullets (joined) if needed
        if rec and paragraph:
            result = {"recommendation": rec, "paragraph": paragraph}
            if bullets:
                result["bullets"] = bullets
            return result
        if rec and bullets:
            joined = " ".join([b.strip() for b in bullets if isinstance(b, str)])
            return {"recommendation": rec, "paragraph": joined, "bullets": bullets}
        return None
    except Exception:
        return None


def _extract_synopsis_from_source(grant: Dict) -> Optional[str]:
    """Best-effort extraction of a program synopsis from grant source text.

    Strategy:
    - Look for a line starting with 'Synopsis:' (common on NSF pages).
    - If not found, look for 'Synopsis of Program:'
    - Return the remainder of that line trimmed. If multiple lines, return the first line.
    - Fallback: None.
    """
    try:
        src = grant.get("source") or {}
        p = src.get("path")
        if not p:
            return None
        path = Path(p)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if line.lower().startswith("synopsis of program:"):
                    return line.split(":", 1)[1].strip() or None
                if line.lower().startswith("synopsis:"):
                    return line.split(":", 1)[1].strip() or None
    except Exception:
        return None
    return None


def _next_deadline(dl: Dict) -> Optional[str]:
    try:
        if not isinstance(dl, dict):
            return None
        dates = dl.get("dates") or []
        if not dates:
            return None
        # Dates are ISO YYYY-MM-DD strings; simple sort works
        return sorted(dates)[0]
    except Exception:
        return None


_ROLLING_HINTS = (
    "proposals accepted anytime",
    "proposals accepted any time",
    "accepts proposals at any time",
    "accepts proposals anytime",
    "continuous submission",
    "continuous submissions",
    "accepted continuously",
    "on a rolling basis",
)


def _has_rolling_phrase(text: str) -> bool:
    s = text.lower()
    return any(h in s for h in _ROLLING_HINTS)


def _rolling_from_source(grant: Dict) -> bool:
    try:
        src = grant.get("source") or {}
        p = src.get("path")
        if not p:
            return False
        path = Path(p)
        if not path.exists():
            return False
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                if _has_rolling_phrase(raw):
                    return True
    except Exception:
        return False
    return False


def _funding_from_source(grant: Dict) -> Optional[Dict]:
    try:
        from extraction.funding_extractor import extract_funding_info
    except Exception:
        return None


def _extract_anticipated_from_source(grant: Dict) -> Optional[str]:
    """Extract 'Anticipated Funding Amount' line verbatim from source text.

    Falls back to common variants like 'Estimated Total Program Funding'.
    Returns the full line content after the colon, or the whole line if no colon.
    """
    try:
        src = grant.get("source") or {}
        p = src.get("path")
        if not p:
            return None
        path = Path(p)
        if not path.exists():
            return None
        patterns = [
            "anticipated funding amount",
            "estimated total program funding",
            "total anticipated program funding",
        ]
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        for i, raw in enumerate(lines):
            line = raw.strip()
            if not line:
                continue
            lcl = line.lower()
            if any(lcl.startswith(pat) for pat in patterns):
                # Split after first colon if present
                if ":" in line:
                    after = line.split(":", 1)[1].strip()
                    if after:
                        return after
                    # If empty, try next non-empty line
                    j = i + 1
                    while j < len(lines):
                        nxt = lines[j].strip()
                        j += 1
                        if nxt:
                            return nxt
                    return None
                return line
        return None
    except Exception:
        return None
    try:
        src = grant.get("source") or {}
        p = src.get("path")
        if not p:
            return None
        path = Path(p)
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
        return extract_funding_info(text)
    except Exception:
        return None


# Cache taxonomy embeddings
_EMB_CACHE: dict[str, dict] = {}

TAX_KEYS = [
    "mission_tags",
    "population_tags",
    "org_type_tags",
    "geography_tags",
    "red_flag_tags",
]


def _load_json(path: Path) -> Dict:
    with open(path, "r") as f:
        return json.load(f)


def _tag_set(profile: Dict, key: str) -> Set[str]:
    items = profile.get("canonical_tags", {}).get(key, [])
    return {d.get("tag") for d in items if isinstance(d, dict) and d.get("tag")}


def _overlap_ratio(org_tags: Set[str], grant_tags: Set[str]) -> float:
    if not org_tags:
        return 0.0
    return len(org_tags & grant_tags) / max(1, len(org_tags))


def _semantic_overlap(taxonomy_name: str, org_tags: Set[str], grant_tags: Set[str]) -> float:
    if not org_tags:
        return 0.0
    try:
        if taxonomy_name not in _EMB_CACHE:
            _EMB_CACHE[taxonomy_name] = load_taxonomy_embeddings(
                str(settings.TAXONOMY_EMBEDDINGS_DIR / f"{taxonomy_name}_embeddings.json")
            )
        emb = _EMB_CACHE.get(taxonomy_name) or {}
        if not emb:
            return _overlap_ratio(org_tags, grant_tags)
    except Exception:
        return _overlap_ratio(org_tags, grant_tags)
    threshold = settings.MATCH_TAX_SIM_THRESHOLD
    scores = []
    import numpy as _np
    for ot in org_tags:
        vec_o = emb.get(ot)
        if not vec_o:
            scores.append(1.0 if ot in grant_tags else 0.0)
            continue
        best = 0.0
        for gt in grant_tags:
            vec_g = emb.get(gt)
            if not vec_g:
                continue
            sim = cosine_similarity(_np.array(vec_o), _np.array(vec_g))
            if sim > best:
                best = sim
        scores.append(best if best >= threshold else 0.0)
    return float(sum(scores) / len(scores)) if scores else 0.0


def _geography_overlap(org_tags: Set[str], grant_tags: Set[str]) -> float:
    if not org_tags:
        return 0.0
    if "us_national" in grant_tags:
        return 1.0 if org_tags else 0.0
    return _overlap_ratio(org_tags, grant_tags)


def _hard_block(org_type_tags: Set[str], grant_red_flags: Set[str]) -> bool:
    rules = settings.MATCH_HARD_BLOCKS
    for rf in grant_red_flags:
        rule = rules.get(rf)
        if not rule:
            continue
        req = rule.get("org_type_tags", {}).get("any_of", [])
        if req and not (org_type_tags & set(req)):
            return True
    return False


def _score_and_reasons(org: Dict, grant: Dict) -> Tuple[float, str, List[str]]:
    o = {k: _tag_set(org, k) for k in TAX_KEYS}
    g = {k: _tag_set(grant, k) for k in TAX_KEYS}
    red_flags_set = set(g["red_flag_tags"]) if g["red_flag_tags"] else set()
    if _hard_block(o["org_type_tags"], red_flags_set):
        return 0.0, "Avoid", [f"Hard block due to red flags: {sorted(red_flags_set)}"]
    w = settings.MATCH_WEIGHTS
    mission = _semantic_overlap("mission_tags", o["mission_tags"], g["mission_tags"]) * w["mission_tags"]
    pop = _semantic_overlap("population_tags", o["population_tags"], g["population_tags"]) * w["population_tags"]
    geo = _geography_overlap(o["geography_tags"], g["geography_tags"]) * w["geography_tags"]
    orgtype = (1.0 if (o["org_type_tags"] & g["org_type_tags"]) else 0.0) * w["org_type_tags"]
    score = mission + pop + geo + orgtype
    if red_flags_set:
        score *= settings.MATCH_RED_FLAG_PENALTY
    score = round(score, 3)
    if score >= settings.MATCH_APPLY_THRESHOLD:
        bucket = "Apply"
    elif score >= settings.MATCH_MAYBE_THRESHOLD:
        bucket = "Maybe"
    else:
        bucket = "Avoid"
    reasons: List[str] = []
    if o["mission_tags"] & g["mission_tags"]:
        reasons.append(f"Mission overlap: {sorted(o['mission_tags'] & g['mission_tags'])}")
    if o["population_tags"] & g["population_tags"]:
        reasons.append(f"Population overlap: {sorted(o['population_tags'] & g['population_tags'])}")
    if o["org_type_tags"] & g["org_type_tags"]:
        reasons.append(f"Org type ok: {sorted(o['org_type_tags'] & g['org_type_tags'])}")
    if o["geography_tags"] & g["geography_tags"]:
        reasons.append(f"Geography overlap: {sorted(o['geography_tags'] & g['geography_tags'])}")
    if red_flags_set:
        reasons.append(f"Red flags: {sorted(red_flags_set)}")
    return score, bucket, reasons


def recommend(org_profile_path: Path, grants_dir: Path, top: int = 10, explain: bool = False) -> Dict:
    org = _load_json(org_profile_path)
    # First pass: score all grants without generating explanations (for ordering).
    raw: List[Dict] = []
    for p in sorted(grants_dir.glob("*_profile.json")):
        try:
            g = _load_json(p)
            score, bucket, reasons = _score_and_reasons(org, g)
            dl = g.get("deadline", {})
            # Derive rolling from source text if extractor missed 'anytime' style phrasing
            dl_status = dl.get("status")
            if (not dl_status or dl_status == "unspecified") and _rolling_from_source(g):
                dl = {**dl, "status": "rolling"}
            fd = g.get("funding", {}) or {}
            # Extract anticipated funding amount text directly (verbatim)
            anticipated = _extract_anticipated_from_source(g)
            raw.append(
                {
                    "grant_profile": p.name,
                    "_grant_path": str(p),  # internal helper for deferred explanation
                    "score": score,
                    "bucket": bucket,
                    "deadlines": dl.get("dates", []),
                    "deadline_status": dl.get("status"),
                    "deadline": _next_deadline(dl),
                    "anticipated_funding_amount": anticipated,
                    "url": (g.get("source") or {}).get("url"),
                    "reasons": reasons,
                }
            )
        except Exception as e:
            raw.append({"grant_profile": p.name, "error": str(e)})

    # Sort by score desc and optionally truncate to top-N for output.
    raw.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    ordered = raw[:top] if top else raw

    # If no explanations requested, strip helper keys and return
    if not explain:
        for item in ordered:
            item.pop("_grant_path", None)
        return {"org_profile": org_profile_path.name, "recommendations": ordered}

    # Explanation gating: only top-K or above score threshold
    top_k = settings.EXPLAIN_TOP_K
    min_score = settings.EXPLAIN_MIN_SCORE
    # Precompute org tag sets once
    o_tags = {k: _tag_set(org, k) for k in TAX_KEYS}

    final_recs: List[Dict] = []
    for idx, item in enumerate(ordered):
        # Items that errored or lack scores are passed through unchanged
        if "error" in item:
            item.pop("_grant_path", None)
            final_recs.append(item)
            continue

        score_val = item.get("score", 0.0) or 0.0
        do_explain = (idx < top_k) or (score_val >= min_score)
        if do_explain:
            # Generate explanation lazily now
            grant_path = Path(item.get("_grant_path", ""))
            try:
                g = _load_json(grant_path) if grant_path.exists() else None
                if g is None:
                    raise FileNotFoundError(str(grant_path))
                g_tags = {k: _tag_set(g, k) for k in TAX_KEYS}
                overlap = {
                    "mission": sorted(o_tags["mission_tags"] & g_tags["mission_tags"]) if o_tags["mission_tags"] else [],
                    "population": sorted(o_tags["population_tags"] & g_tags["population_tags"]) if o_tags["population_tags"] else [],
                    "org_type": sorted(o_tags["org_type_tags"] & g_tags["org_type_tags"]) if o_tags["org_type_tags"] else [],
                    "geography": sorted(o_tags["geography_tags"] & g_tags["geography_tags"]) if o_tags["geography_tags"] else [],
                }
                exp = _generate_explanation(org, g, overlap)
                if exp:
                    # Keep only paragraph string in output
                    para = None
                    if isinstance(exp, dict):
                        para = exp.get("paragraph")
                        if (not para) and isinstance(exp.get("bullets"), list):
                            para = " ".join([b.strip() for b in exp["bullets"] if isinstance(b, str)])
                    if isinstance(exp, str):
                        para = exp
                    if para:
                        item["explanation"] = para
                # Also attach a simple program synopsis if present
                syn = _extract_synopsis_from_source(g)
                if syn:
                    item["synopsis"] = syn
            except Exception as _:
                # If explanation fails, just continue without it
                pass
            item.pop("_grant_path", None)
            final_recs.append(item)
        else:
            # For non-explained items, keep the full base fields (no explanation)
            item.pop("_grant_path", None)
            final_recs.append(item)

    return {"org_profile": org_profile_path.name, "recommendations": final_recs}


def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Rank grants for an org profile using tag overlaps.")
    parser.add_argument("--org", required=True, help="Path to org profile JSON.")
    parser.add_argument("--grants", default=str((settings.PROCESSED_GRANTS_DIR).resolve()), help="Directory of grant profile JSONs.")
    parser.add_argument("--top", type=int, default=10, help="Top-N results to return (0 = all).")
    parser.add_argument("--out", help="Optional output JSON file path.")
    parser.add_argument("--explain", action="store_true", help="Include LLM-generated explanation paragraph.")
    args = parser.parse_args(argv)
    org_path = Path(args.org)
    grants_dir = Path(args.grants)
    if not org_path.exists():
        print(f"[error] Org profile not found: {org_path}")
        return 1
    if not grants_dir.exists() or not grants_dir.is_dir():
        print(f"[error] Grants directory not found: {grants_dir}")
        return 1
    result = recommend(org_path, grants_dir, top=args.top, explain=args.explain)
    if args.out:
        out_path = Path(args.out)
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"[ok] Wrote recommendations → {out_path}")
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
