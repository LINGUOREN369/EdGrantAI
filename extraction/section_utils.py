"""
NSF section splitting and phrase provenance utilities.

Provides:
- split_nsf_sections(text) -> list of (start, end, label)
- assign_sections_to_phrases(phrases, text) -> list of {text, section}

Sections detected (case-insensitive, with or without Roman numerals):
- Introduction
- Program Description
- Award Information
- Eligibility Information
If no section header is found, the entire text is labeled as "Other".
"""

from __future__ import annotations

import re
from typing import List, Tuple, Dict


SECTION_LABELS = [
    "Introduction",
    "Program Description",
    "Award Information",
    "Eligibility Information",
]


def split_nsf_sections(text: str) -> List[Tuple[int, int, str]]:
    lines = text.splitlines(keepends=True)
    # Build regexes for headings with optional Roman numerals
    pats = [
        ("Introduction", re.compile(r"^\s*(?:I\.)?\s*Introduction\b", re.I)),
        ("Program Description", re.compile(r"^\s*(?:II\.)?\s*Program\s+Description\b", re.I)),
        ("Award Information", re.compile(r"^\s*(?:III\.)?\s*Award\s+Information\b", re.I)),
        ("Eligibility Information", re.compile(r"^\s*(?:IV\.)?\s*Eligibility\s+Information\b", re.I)),
    ]
    # Fallback aliases often used by NSF; map to closest label
    aliases = [
        ("Introduction", re.compile(r"^\s*Synopsis\s+of\s+Program\b|^\s*Summary\s+of\s+Program\s+Requirements\b", re.I)),
    ]

    # Scan and record heading positions
    pos = 0
    found: List[Tuple[int, str]] = []
    for ln in lines:
        for label, rx in pats + aliases:
            if rx.search(ln):
                found.append((pos, label))
                break
        pos += len(ln)

    if not found:
        # Single block as Other
        return [(0, len(text), "Other")]

    # Sort and build spans
    found.sort(key=lambda t: t[0])
    spans: List[Tuple[int, int, str]] = []
    for i, (start, label) in enumerate(found):
        end = found[i + 1][0] if i + 1 < len(found) else len(text)
        spans.append((start, end, label))
    return spans


def assign_sections_to_phrases(phrases: List[str], text: str) -> List[Dict[str, str]]:
    spans = split_nsf_sections(text)
    result: List[Dict[str, str]] = []

    def _find_section_index(idx: int) -> str:
        for s, e, label in spans:
            if s <= idx < e:
                return label
        return "Other"

    for p in phrases:
        if not p:
            result.append({"text": p, "section": "Other"})
            continue
        # Try exact search first, then case-insensitive
        idx = text.find(p)
        if idx == -1:
            m = re.search(re.escape(p), text, flags=re.I)
            idx = m.start() if m else -1
        label = _find_section_index(idx) if idx != -1 else "Other"
        result.append({"text": p, "section": label})
    return result

