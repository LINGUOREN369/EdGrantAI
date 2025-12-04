"""
Auto-generate safe, format-level synonyms for taxonomy tags.

Generates up to N synonyms per tag using conservative transformations:
 - Parenthetical acronyms (e.g., "open educational resources (OER)" → "OER", "open educational resources")
 - K–12 variants (K-12 / K–12 / K12 / "K to 12" / "K through 12")
 - And/& alternation ("a and b" ↔ "a & b")
 - Singular/plural (students/student, teachers/teacher, agencies/agency, ministries/ministry)
 - Hyphen vs space variants (usually redundant due to normalization but harmless)
 - Common short forms (postdoctoral→postdoc, preproposal→pre-proposal, organization→org)

Outputs JSON files under data/taxonomy/synonyms/<taxonomy>_synonyms.auto.json

Usage:
  python -m pipeline.build_synonyms --all [--max 10]
  python -m pipeline.build_synonyms --names mission_tags population_tags --max 8
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Set

from .config import settings


SYN_DIR = settings.TAXONOMY_DIR / "synonyms"
SYN_DIR.mkdir(parents=True, exist_ok=True)


def _load_tags(name: str) -> List[str]:
    path = settings.TAXONOMY_DIR / f"{name}.json"
    with open(path, "r") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {path}")
    return [t for t in data if isinstance(t, str)]


def _singularize(token: str) -> str:
    if token.endswith("ies"):
        return token[:-3] + "y"
    if token.endswith("ses"):
        return token[:-2]
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _k12_variants(s: str) -> List[str]:
    out = []
    if re.search(r"k\s*[–-]?\s*12", s, re.I):
        out.extend(["K-12", "K–12", "K12", "K to 12", "K through 12"]) 
    return out


def _paren_acronym_variants(s: str) -> List[str]:
    out = []
    m = re.search(r"^(.*?)\(([^)]+)\)\s*$", s)
    if m:
        long = m.group(1).strip()
        acro = m.group(2).strip()
        if long:
            out.append(long)
        if acro and 2 <= len(acro) <= 12:
            out.append(acro)
    return out


def _and_amp_variants(s: str) -> List[str]:
    out = []
    if " and " in s:
        out.append(s.replace(" and ", " & "))
    if " & " in s:
        out.append(s.replace(" & ", " and "))
    return out


def _hyphen_space_variants(s: str) -> List[str]:
    if "-" in s:
        return [s.replace("-", " ")]
    return []


def _short_forms(s: str) -> List[str]:
    out = []
    # domain-safe short forms
    repl = {
        "postdoctoral": "postdoc",
        "preproposal": "pre-proposal",
        "organization": "org",
    }
    for k, v in repl.items():
        if k in s:
            out.append(s.replace(k, v))
    return out


def _singular_plural_variants(s: str) -> List[str]:
    out = []
    # Only apply to last token to reduce harm
    tokens = s.split()
    if not tokens:
        return out
    last = tokens[-1]
    sg = _singularize(last)
    if sg != last:
        out.append(" ".join(tokens[:-1] + [sg]))
    return out


def generate_synonyms_for_tag(tag: str, taxonomy_name: str) -> List[str]:
    s = tag.strip()
    syns: List[str] = []
    syns += _paren_acronym_variants(s)
    syns += _k12_variants(s)
    syns += _and_amp_variants(s)
    syns += _hyphen_space_variants(s)
    syns += _short_forms(s)
    syns += _singular_plural_variants(s)

    # Geography-specific safe expansions
    if taxonomy_name == "geography_tags":
        if s.lower() == "united states":
            syns += ["US", "U.S.", "USA", "U.S.A."]
        if s.lower() == "global":
            syns += ["worldwide", "international", "around the world", "across the globe"]

    # Red flags safe expansions
    if taxonomy_name == "red_flag_tags":
        mapping = {
            "letter of intent required": ["letter of intent", "LOI"],
            "preproposal required": ["preproposal", "pre-proposal"],
            "IRB approval required": ["IRB", "human subjects"],
            "data management and sharing plan": ["data management plan"],
            "postdoctoral mentoring plan": ["postdoc mentoring plan", "mentoring plan"],
            "letters of collaboration": ["collaboration letters"],
        }
        if tag in mapping:
            syns += mapping[tag]

    # NSF programs acronyms (uppercased) — already handled via manual synonyms file, but ensure here too
    if taxonomy_name == "nsf_programs":
        m = re.search(r"\(([^)]+)\)$", s)
        if m:
            acro = m.group(1).strip()
            if acro:
                syns.append(acro)

    # Dedup and return
    seen: Set[str] = set()
    out = []
    for syn in syns:
        syn_norm = syn.strip()
        if syn_norm and syn_norm.lower() != s.lower() and syn_norm not in seen:
            out.append(syn_norm)
            seen.add(syn_norm)
    return out


def build_for_taxonomy(name: str, max_per_tag: int = 10) -> Path:
    tags = _load_tags(name)
    out_map: Dict[str, str] = {}
    for tag in tags:
        syns = generate_synonyms_for_tag(tag, name)
        for syn in syns[:max_per_tag]:
            out_map[syn] = tag
    out_path = SYN_DIR / f"{name}_synonyms.auto.json"
    with open(out_path, "w") as f:
        json.dump(out_map, f, indent=2)
    print(f"[ok] wrote {len(out_map)} synonyms → {out_path}")
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Auto-generate safe synonym maps for taxonomy tags.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Generate for all default taxonomies.")
    group.add_argument("--names", nargs="+", metavar="NAME", help="Specific taxonomy names.")
    parser.add_argument("--max", type=int, default=10, help="Max synonyms per tag (default 10).")
    args = parser.parse_args(argv)

    names = args.names if args.names else ([] if not args.all else settings.TAXONOMIES + ["nsf_programs"])
    if not names:
        names = settings.TAXONOMIES + ["nsf_programs"]

    for name in names:
        try:
            build_for_taxonomy(name, max_per_tag=args.max)
        except Exception as e:
            print(f"[error] {name}: {e}")
            return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

