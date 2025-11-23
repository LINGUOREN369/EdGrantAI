from __future__ import annotations

from typing import Dict, List


def check_eligibility(project: Dict, eligibility: List[str]) -> float:
    """
    Simple rule check: if project declares nonprofit/501c3 and geographic hints.
    Returns a multiplier between 0.7 and 1.1.
    """
    multip = 1.0
    text = (project.get("profile") or "").lower()

    if any(k in text for k in ["501(c)(3)", "501c3", "nonprofit", "non-profit"]):
        if any("501(c)(3)" in e.lower() or "nonprofit" in e.lower() for e in eligibility):
            multip += 0.05

    if "us" in text or "united states" in text:
        if any("us" in e.lower() or "united states" in e.lower() for e in eligibility):
            multip += 0.05

    # If eligibility mentions state/local and project not, apply slight penalty
    if any("state" in e.lower() or "local" in e.lower() for e in eligibility) and not any(
        k in text for k in ["state", "county", "city", "district"]
    ):
        multip -= 0.1

    return max(0.7, min(1.1, multip))

