from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from matching.pipeline import run_matching

DATA_STRUCTURED_DIR = Path(os.getenv("DATA_STRUCTURED_DIR", "./data/structured"))


app = FastAPI(title="EdGrant AI API", version="0.1.0")


class MatchRequest(BaseModel):
    project_description: str
    top_k: int = 5


class ExplainRequest(BaseModel):
    project_description: str
    grant_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


def _load_grant_by_id(grant_id: str) -> Dict[str, Any]:
    for fp in DATA_STRUCTURED_DIR.glob("*.json"):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            if data.get("id") == grant_id:
                return data
        except Exception:
            continue
    raise HTTPException(status_code=404, detail="Grant not found")


@app.post("/match")
def match(req: MatchRequest):
    results = run_matching(req.project_description, top_k=req.top_k)
    return {"results": results}


@app.post("/explain")
def explain(req: ExplainRequest):
    from reasoning.llm_reasoner import generate_fit_explanation, assess_risks, suggest_narrative_angles

    grant = _load_grant_by_id(req.grant_id)
    evidence = grant.get("summary") or ""
    fit = generate_fit_explanation(req.project_description, grant.get("title", ""), grant.get("funder") or "", evidence)
    risks = assess_risks(req.project_description, evidence)
    angles = suggest_narrative_angles(req.project_description, evidence)
    return {"grant_id": req.grant_id, "fit": fit, "risks": risks, "narrative_angles": angles}


@app.get("/grant/{grant_id}")
def get_grant(grant_id: str):
    return _load_grant_by_id(grant_id)

