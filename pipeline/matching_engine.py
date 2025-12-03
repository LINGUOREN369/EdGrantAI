"""
Matching engine: rank grant profiles for a given organization profile.

Scoring logic (configurable via pipeline.config.settings):
- Mission overlap (weight)
- Population overlap (weight)
- Geography overlap (weight)
- Org type match (binary, weight)
- Red flags (penalty multiplier when present)

CLI usage:
- Single org vs. directory of grant profiles (JSON):
  - python -m pipeline.matching_engine --org data/processed_orgs/mmsa_profile.json --grants data/processed_grants --top 10
- Output to a JSON file:
  - python -m pipeline.matching_engine --org ... --grants ... --out recs.json

Output structure:
{
  "org_profile": "mmsa_profile.json",
  "recommendations": [
    {
      "grant_profile": "nsf_AISL_profile.json",
      "score": 0.71,
      "bucket": "Apply",
      "deadlines": ["2025-01-08"],
      "deadline_status": "date",
      "funding_min": 5000,
      "funding_max": 50000,
      "reasons": ["Mission overlap: [...]", "Population overlap: [...]", "Org type ok: [...]", "Geography overlap: [...]", "Red flags: [...]"]
    },
    ...
  ]
}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from .config import settings
from .embedding_matcher import load_taxonomy_embeddings, cosine_similarity


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


def _semantic_overlap(
    taxonomy_name: str,
    org_tags: Set[str],
    grant_tags: Set[str],
) -> float:
    """
    Compute semantic overlap between org and grant tag sets for a taxonomy
    using precomputed taxonomy tag embeddings. For each org tag, take the
    maximum cosine similarity to any grant tag, then average across org tags.

    Similarities below MATCH_TAX_SIM_THRESHOLD are treated as zero.
    Fallback to exact overlap ratio if embeddings are missing or tag not found.
    """
    if not org_tags:
        return 0.0
    try:
        emb = load_taxonomy_embeddings(str(settings.TAXONOMY_EMBEDDINGS_DIR / f"{taxonomy_name}_embeddings.json"))
    except Exception:
        return _overlap_ratio(org_tags, grant_tags)

    threshold = settings.MATCH_TAX_SIM_THRESHOLD
    scores = []
    for ot in org_tags:
        vec_o = emb.get(ot)
        if not vec_o:
            # unknown tag in embeddings: fallback to exact membership
            scores.append(1.0 if ot in grant_tags else 0.0)
            continue
        best = 0.0
        for gt in grant_tags:
            vec_g = emb.get(gt)
            if not vec_g:
                continue
            sim = cosine_similarity(__import__('numpy').array(vec_o), __import__('numpy').array(vec_g))
            if sim > best:
                best = sim
        scores.append(best if best >= threshold else 0.0)
    # Average across org tags
    return float(sum(scores) / len(scores)) if scores else 0.0


def _geography_overlap(org_tags: Set[str], grant_tags: Set[str]) -> float:
    """Geography with simple superset rules.

    - If grant includes us_national → full match when org has any US geography tag.
    - Otherwise use exact overlap ratio.
    """
    if not org_tags:
        return 0.0
    if "us_national" in grant_tags:
        # Treat as superset; if org has any geography tag, count full
        return 1.0 if org_tags else 0.0
    return _overlap_ratio(org_tags, grant_tags)


def _hard_block(org_type_tags: Set[str], grant_red_flags: Set[str]) -> bool:
    """Return True if any configured red-flag hard block applies and org types
    do not satisfy the requirement."""
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

    # Hard block on certain red flags
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
    if o["mission_tags"]:
        inter = o["mission_tags"] & g["mission_tags"]
        if inter:
            reasons.append(f"Mission overlap: {sorted(inter)}")
    if o["population_tags"]:
        inter = o["population_tags"] & g["population_tags"]
        if inter:
            reasons.append(f"Population overlap: {sorted(inter)}")
    if o["org_type_tags"] & g["org_type_tags"]:
        reasons.append(f"Org type ok: {sorted(o['org_type_tags'] & g['org_type_tags'])}")
    if o["geography_tags"] & g["geography_tags"]:
        reasons.append(f"Geography overlap: {sorted(o['geography_tags'] & g['geography_tags'])}")
    if red_flags_set:
        reasons.append(f"Red flags: {sorted(red_flags_set)}")

    return score, bucket, reasons


def recommend(org_profile_path: Path, grants_dir: Path, top: int = 10) -> Dict:
    org = _load_json(org_profile_path)
    recs: List[Dict] = []
    for p in sorted(grants_dir.glob("*_profile.json")):
        try:
            g = _load_json(p)
            score, bucket, reasons = _score_and_reasons(org, g)
            dl = g.get("deadline", {})
            fd = g.get("funding", {})
            recs.append(
                {
                    "grant_profile": p.name,
                    "score": score,
                    "bucket": bucket,
                    "deadlines": dl.get("dates", []),
                    "deadline_status": dl.get("status"),
                    "funding_min": fd.get("estimated_min"),
                    "funding_max": fd.get("estimated_max"),
                    "reasons": reasons,
                }
            )
        except Exception as e:
            recs.append({"grant_profile": p.name, "error": str(e)})

    recs.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return {"org_profile": org_profile_path.name, "recommendations": recs[:top] if top else recs}


def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Rank grants for an org profile using tag overlaps.")
    parser.add_argument("--org", required=True, help="Path to org profile JSON (from org_profile_builder).")
    parser.add_argument("--grants", default=str((settings.PROCESSED_GRANTS_DIR).resolve()), help="Directory of grant profile JSONs.")
    parser.add_argument("--top", type=int, default=10, help="Top-N results to return (0 = all).")
    parser.add_argument("--out", help="Optional output JSON file path (writes recommendations).")

    args = parser.parse_args(argv)
    org_path = Path(args.org)
    grants_dir = Path(args.grants)

    if not org_path.exists():
        print(f"[error] Org profile not found: {org_path}")
        return 1
    if not grants_dir.exists() or not grants_dir.is_dir():
        print(f"[error] Grants directory not found: {grants_dir}")
        return 1

    result = recommend(org_path, grants_dir, top=args.top)
    if args.out:
        out_path = Path(args.out)
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"[ok] Wrote recommendations → {out_path}")
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
