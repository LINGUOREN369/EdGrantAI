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
        bullets = data.get("bullets") if isinstance(data.get("bullets"), list) else None
        if not rec or not bullets:
            return None
        return {"recommendation": rec, "bullets": bullets}
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
    recs: List[Dict] = []
    for p in sorted(grants_dir.glob("*_profile.json")):
        try:
            g = _load_json(p)
            score, bucket, reasons = _score_and_reasons(org, g)
            dl = g.get("deadline", {})
            fd = g.get("funding", {})
            item = {
                "grant_profile": p.name,
                "score": score,
                "bucket": bucket,
                "deadlines": dl.get("dates", []),
                "deadline_status": dl.get("status"),
                "funding_min": fd.get("estimated_min"),
                "funding_max": fd.get("estimated_max"),
                "reasons": reasons,
            }
            if explain:
                o = {k: _tag_set(org, k) for k in TAX_KEYS}
                gg = {k: _tag_set(g, k) for k in TAX_KEYS}
                overlap = {
                    "mission": sorted(o["mission_tags"] & gg["mission_tags"]) if o["mission_tags"] else [],
                    "population": sorted(o["population_tags"] & gg["population_tags"]) if o["population_tags"] else [],
                    "org_type": sorted(o["org_type_tags"] & gg["org_type_tags"]) if o["org_type_tags"] else [],
                    "geography": sorted(o["geography_tags"] & gg["geography_tags"]) if o["geography_tags"] else [],
                }
                exp = _generate_explanation(org, g, overlap)
                if exp:
                    item["explanation"] = exp
            recs.append(item)
        except Exception as e:
            recs.append({"grant_profile": p.name, "error": str(e)})
    recs.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return {"org_profile": org_profile_path.name, "recommendations": recs[:top] if top else recs}


def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Rank grants for an org profile using tag overlaps.")
    parser.add_argument("--org", required=True, help="Path to org profile JSON.")
    parser.add_argument("--grants", default=str((settings.PROCESSED_GRANTS_DIR).resolve()), help="Directory of grant profile JSONs.")
    parser.add_argument("--top", type=int, default=10, help="Top-N results to return (0 = all).")
    parser.add_argument("--out", help="Optional output JSON file path.")
    parser.add_argument("--explain", action="store_true", help="Include LLM-generated explanation bullets.")
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

