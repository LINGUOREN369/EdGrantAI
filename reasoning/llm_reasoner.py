from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

load_dotenv()

TPL_DIR = Path(__file__).parent / "templates"


def _render_template(name: str, ctx: Dict) -> str:
    tpl = (TPL_DIR / name).read_text(encoding="utf-8")
    for k, v in ctx.items():
        tpl = tpl.replace("{" + k + "}", str(v))
    return tpl


def _llm_generate(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Fallback: echo-style output for local/dev
        return "[LLM disabled] " + prompt[:500]
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        msg = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return msg.choices[0].message.content or ""
    except Exception:
        return "[LLM error or blocked; using template text] " + prompt[:500]


def generate_fit_explanation(project_description: str, grant_title: str, funder: str, evidence: str) -> str:
    prompt = _render_template(
        "fit.md",
        {
            "project_description": project_description,
            "grant_title": grant_title or "",
            "funder": funder or "",
            "evidence": evidence or "",
        },
    )
    return _llm_generate(prompt)


def assess_risks(project_description: str, evidence: str) -> str:
    prompt = _render_template(
        "risks.md",
        {
            "project_description": project_description,
            "evidence": evidence or "",
        },
    )
    return _llm_generate(prompt)


def suggest_narrative_angles(project_description: str, evidence: str) -> str:
    prompt = _render_template(
        "narrative_angle.md",
        {
            "project_description": project_description,
            "evidence": evidence or "",
        },
    )
    return _llm_generate(prompt)

