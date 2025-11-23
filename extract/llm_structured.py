from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .regex_helpers import guess_amount, guess_deadline
from .schema import GrantSchema

load_dotenv()


def _make_id(text: str, url: Optional[str]) -> str:
    seed = (url or "") + "|" + text[:400]
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


def extract_structured(text: str, url: Optional[str] = None) -> GrantSchema:
    """
    Lightweight structurer stub. If OPENAI_API_KEY is present, you may wire in
    a JSON-mode call; by default we apply simple heuristics and placeholders
    to create a minimally useful GrantSchema.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = lines[0][:200] if lines else "Untitled Grant"
    summary = " ".join(lines[1:6])[:600] if len(lines) > 1 else None

    deadline_s = guess_deadline(text)
    deadline = None
    if deadline_s:
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%b %d, %Y", "%B %d, %Y"):
            try:
                deadline = datetime.strptime(deadline_s, fmt).date()
                break
            except Exception:
                continue

    amount = guess_amount(text)
    tags = []
    lower = text.lower()
    for kw in ["k-12", "stem", "edtech", "curriculum", "professional development", "teacher", "student"]:
        if kw in lower:
            tags.append(kw)

    # naive eligibility bullets
    eligibility = []
    for key in ["501(c)(3)", "nonprofit", "public school", "us only", "state", "local"]:
        if key.lower() in lower:
            eligibility.append(key)

    sid = _make_id(text, url)
    return GrantSchema(
        id=sid,
        title=title,
        funder=None,
        url=url,
        summary=summary,
        eligibility=eligibility,
        deadline=deadline,
        amount=amount,
        tags=tags,
    )


def save_schema_json(schema: GrantSchema, out_path: str | Path) -> Path:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(schema.model_dump_json(indent=2), encoding="utf-8")
    return p

