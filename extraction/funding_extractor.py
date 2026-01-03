"""
Deterministic funding extractor.

Parses funding/award amounts from grant/RFP text using simple, transparent
regex heuristics. Returns a structured summary with estimated min/max and
raw mention lines.

Output shape:
{
  "estimated_min": int | None,  # dollars
  "estimated_max": int | None,  # dollars
  "raw_mentions": ["Maximum award size is $500,000", ...]
}

Heuristics:
- Only considers lines with funding-related cues (award, grant, budget, max/min,
  up to, not to exceed, range, between, from ... to ...).
- Ignores program-wide totals (e.g., "Estimated Total Program Funding").
- Recognizes amounts like $500,000, $500k, $0.5M, 500k, 1.2 million, 2 billion.
- For ranges (between X and Y, X–Y, X to Y), sets min=X, max=Y.
- For "up to"/"maximum"/"not to exceed": sets max.
- For "minimum"/"at least": sets min.
- For a single standalone amount: sets both min and max to that value.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple


# Positive line-level cues
_FUNDING_CUES = re.compile(
    r"\b(award|awards|grant|grants|budget|maximum|max|minimum|min|up to|not to exceed|per award|award size|per project|each award)\b",
    re.IGNORECASE,
)

# Negative filters (program-level totals rather than per-award sizes)
_IGNORE_LINE = re.compile(
    r"\b(total program funding|estimated total program funding|program budget|total available|available funding)\b",
    re.IGNORECASE,
)

# Money tokens: optional $, number with commas/decimals, optional unit suffix
_MONEY_TOKEN = re.compile(
    r"(?P<prefix>\$)?\s*(?P<num>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(?P<unit>k|K|m|M|b|B|thousand|million|billion)?\b"
)

# Phrases indicating a range
_RANGE_CUES = re.compile(r"\b(between|from)\b|\bto\b|[\u2013\u2014\-]\s*")  # en/em dash or hyphen

# Cues indicating direction
_MAX_CUES = re.compile(r"\b(up to|not to exceed|maximum|max)\b", re.IGNORECASE)
_MIN_CUES = re.compile(r"\b(at least|minimum|min|no less than)\b", re.IGNORECASE)


def _parse_amount(tok: re.Match) -> Optional[int]:
    num_s = tok.group("num")
    unit = tok.group("unit") or ""
    prefix = tok.group("prefix")
    if not (prefix or unit):
        # Require $ or a unit suffix to reduce false positives
        return None
    try:
        n = float(num_s.replace(",", ""))
    except Exception:
        return None
    u = unit.lower()
    mult = 1.0
    if u in ("k", "thousand"):
        mult = 1e3
    elif u in ("m", "million"):
        mult = 1e6
    elif u in ("b", "billion"):
        mult = 1e9
    # Round to nearest dollar
    val = int(round(n * mult))
    # Discard out-of-range values to avoid program totals or spurious tokens
    if val < 1000 or val > 100_000_000:
        return None
    return val


def _extract_amounts(line: str) -> List[int]:
    vals: List[int] = []
    for m in _MONEY_TOKEN.finditer(line):
        v = _parse_amount(m)
        if v is not None:
            vals.append(v)
    return vals


def extract_funding_info(text: str) -> Dict:
    mentions: List[str] = []
    mins: List[int] = []
    maxs: List[int] = []
    singles: List[int] = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if _IGNORE_LINE.search(line):
            continue
        if not _FUNDING_CUES.search(line):
            continue
        vals = _extract_amounts(line)
        if not vals:
            continue
        # Record raw mention (limited later)
        if line not in mentions:
            mentions.append(line)

        # Range detection heuristics
        if len(vals) >= 2 and _RANGE_CUES.search(line):
            lo, hi = min(vals[0], vals[1]), max(vals[0], vals[1])
            mins.append(lo)
            maxs.append(hi)
            continue

        # Directional cues
        if _MAX_CUES.search(line):
            maxs.append(max(vals))  # conservative: the largest mentioned
            # if also indicates minimum in same line, capture
            if _MIN_CUES.search(line):
                mins.append(min(vals))
            continue
        if _MIN_CUES.search(line):
            mins.append(min(vals))
            continue

        # Fallback: single amount => treat as both
        singles.extend(vals)

    est_min: Optional[int] = None
    est_max: Optional[int] = None

    if mins and maxs:
        est_min = min(mins)
        est_max = max(maxs)
    elif mins and not maxs:
        est_min = min(mins)
        # Try to infer a max from singles if plausible
        est_max = max(singles) if singles else None
    elif maxs and not mins:
        est_max = max(maxs)
        # Try to infer a min from singles if plausible
        est_min = min(singles) if singles else None
    elif singles:
        # Use spread of singles; treat as both the same if only one
        est_min = min(singles)
        est_max = max(singles)

    return {
        "estimated_min": est_min,
        "estimated_max": est_max,
        "raw_mentions": mentions[:10],
    }
