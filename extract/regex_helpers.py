from __future__ import annotations

import re
from typing import Optional

DATE_RE = re.compile(r"\b(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4}|(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s*\d{4})\b", re.IGNORECASE)
AMOUNT_RE = re.compile(r"\$\s?([0-9][0-9,]*)(?:\s?-\s?\$?([0-9][0-9,]*))?", re.IGNORECASE)


def guess_deadline(text: str) -> Optional[str]:
    m = DATE_RE.search(text)
    return m.group(0) if m else None


def guess_amount(text: str) -> Optional[str]:
    m = AMOUNT_RE.search(text)
    if not m:
        return None
    if m.group(2):
        return f"${m.group(1)} - ${m.group(2)}"
    return f"${m.group(1)}"

