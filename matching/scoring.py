from __future__ import annotations

from typing import Dict, List

from .vertical_weights import VERTICAL_WEIGHTS
from .eligibility_rules import check_eligibility


def weighted_score(similarity: float, grant_meta: Dict, project: Dict) -> float:
    # base sim in [0, 1] (approx)
    score = similarity

    # domain weights
    tags = [t.lower() for t in grant_meta.get("tags", []) or []]
    for t in tags:
        score *= VERTICAL_WEIGHTS.get(t, 1.0)

    # eligibility multiplier
    elig_mult = check_eligibility(project, grant_meta.get("eligibility", []) or [])
    score *= elig_mult

    # clip
    return max(0.0, min(1.5, score))

