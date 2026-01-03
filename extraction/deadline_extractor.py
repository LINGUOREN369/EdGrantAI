"""
Deadline extractor (deterministic heuristics).

Parses common deadline patterns from grant/RFP text and returns a
structured summary suitable for inclusion in a profile.

Output shape:
{
  "status": "date" | "rolling" | "multiple" | "unspecified",
  "dates": ["YYYY-MM-DD", ...],
  "raw_mentions": ["Deadline: March 15, 2025", ...]
}

Notes:
- This is a best-effort, regex-based extractor. It prefers simplicity and
  transparency over perfect coverage. It focuses on lines containing
  typical markers (deadline, due, submit by) and common date formats.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional


_LINE_HINT = re.compile(
    r"\b("
    r"deadline|due date|due|submit by|submission deadline|closing date|"
    r"target date|submission window|full proposal|full proposals|"
    r"loi due|letter of intent|pre[- ]?proposal|preproposal"
    r")\b",
    re.IGNORECASE,
)

# Lines that should NOT be considered as deadlines even if a date is present
_NEGATIVE_HINT = re.compile(
    r"\b(posted|posted date|post date|posted on|publish|published|publication|release date|posted date \(y-m-d\))\b",
    re.IGNORECASE,
)

_ROLLING = re.compile(
    r"\b("
    r"rolling|ongoing|year[- ]round|open until|until filled|no deadline|"
    r"proposals?\s+accepted\s+any\s*time|proposals?\s+accepted\s+anytime|"
    r"accepts?\s+proposals?\s+at\s+any\s*time|accepts?\s+proposals?\s+anytime|"
    r"continuous\s+submission|continuous\s+submissions|"
    r"accepted\s+continuously|accepted\s+on\s+a\s+rolling\s+basis|"
    r"proposals?\s+accepted\s+on\s+a\s+rolling\s+basis"
    r")\b",
    re.IGNORECASE,
)

# Month name patterns (Jan/January etc.) and numeric dates
_DATE_TOKENS = re.compile(
    r"(\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*\d{4})?\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{4}-\d{1,2}-\d{1,2}\b)",
    re.IGNORECASE,
)

_CLEAN_ORD = re.compile(r"(\d+)(st|nd|rd|th)", re.IGNORECASE)


def _norm_date_token(tok: str) -> Optional[str]:
    """Try to normalize a date token to ISO YYYY-MM-DD.

    Supports:
    - Month name DD, YYYY (and without comma)
    - Mon DD, YYYY
    - MM/DD/YYYY or MM/DD/YY
    - YYYY-MM-DD
    Returns None if parsing fails or no year is present.
    """
    s = tok.strip()
    s = _CLEAN_ORD.sub(r"\1", s)  # remove ordinal suffix

    fmts = [
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%Y-%m-%d",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.date().isoformat()
        except Exception:
            continue
    # If no year present, we do not guess
    return None


def extract_deadline_info(text: str) -> Dict:
    lines = text.splitlines()
    mentions: List[str] = []
    dates: List[str] = []
    rolling = False

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        # Skip lines that clearly refer to posting/publishing rather than due dates
        if _NEGATIVE_HINT.search(line):
            continue
        if _ROLLING.search(line):
            rolling = True
        # Only consider lines that have explicit deadline-like cues or rolling hints
        if _LINE_HINT.search(line) or _ROLLING.search(line):
            if line not in mentions:
                mentions.append(line)
            for m in _DATE_TOKENS.finditer(line):
                iso = _norm_date_token(m.group(0))
                if iso and iso not in dates:
                    dates.append(iso)

    status = "unspecified"
    if dates and len(dates) == 1:
        status = "date"
    elif dates and len(dates) > 1:
        status = "multiple"
    elif rolling:
        status = "rolling"

    return {
        "status": status,
        "dates": dates[:5],
        "raw_mentions": mentions[:10],
    }
