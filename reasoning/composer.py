from __future__ import annotations

from typing import Dict, List

from matching.pipeline import run_matching
from .llm_reasoner import generate_fit_explanation, assess_risks, suggest_narrative_angles


def compose_reasoning(project_description: str, top_k: int = 3) -> Dict:
    matches = run_matching(project_description, top_k=top_k)
    results: List[Dict] = []
    for m in matches:
        evidence = m.get("snippet", "")
        fit = generate_fit_explanation(project_description, m.get("title") or "", (m.get("meta") or {}).get("funder") or "", evidence)
        risks = assess_risks(project_description, evidence)
        angles = suggest_narrative_angles(project_description, evidence)
        results.append({
            "grant_id": m.get("grant_id"),
            "title": m.get("title"),
            "score": m.get("score"),
            "fit": fit,
            "risks": risks,
            "narrative_angles": angles,
        })
    return {"project": project_description, "results": results}

