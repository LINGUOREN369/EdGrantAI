"""
Merge auto-generated synonyms into curated synonym files.

For each taxonomy, load:
 - Manual/curated map: data/taxonomy/synonyms/<name>_synonyms.json (if present)
 - Auto map:           data/taxonomy/synonyms/<name>_synonyms.auto.json (if present)

Then write back a single curated file (manual takes precedence on conflicts).
Optionally delete the auto files with --delete-auto.

Usage:
  python -m pipeline.merge_auto_synonyms --all [--delete-auto]
  python -m pipeline.merge_auto_synonyms --names mission_tags population_tags --delete-auto
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from .config import settings


def _load_map(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    with open(path, "r") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {}
    # Keep only string→string
    out: Dict[str, str] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, str) and k and v:
            out[k] = v
    return out


def _write_map(path: Path, m: Dict[str, str]) -> None:
    # Sort keys for stable diffs
    items = {k: m[k] for k in sorted(m.keys(), key=lambda x: x.lower())}
    with open(path, "w") as f:
        json.dump(items, f, indent=2)


def merge_for_taxonomy(name: str, delete_auto: bool = False) -> Path | None:
    syn_dir = settings.TAXONOMY_DIR / "synonyms"
    syn_dir.mkdir(parents=True, exist_ok=True)
    manual_path = syn_dir / f"{name}_synonyms.json"
    auto_path = syn_dir / f"{name}_synonyms.auto.json"

    manual = _load_map(manual_path)
    auto = _load_map(auto_path)

    if not manual and not auto:
        return None

    # manual precedence
    merged = dict(auto)
    merged.update(manual)

    _write_map(manual_path, merged)

    if delete_auto and auto_path.exists():
        try:
            auto_path.unlink()
        except Exception:
            pass
    return manual_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Merge auto synonyms into curated files.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Process all default taxonomies + nsf_programs.")
    group.add_argument("--names", nargs="+", metavar="NAME", help="Specific taxonomy names.")
    parser.add_argument("--delete-auto", action="store_true", help="Delete *.auto.json after merging.")
    args = parser.parse_args(argv)

    names: List[str]
    if args.names:
        names = args.names
    elif args.all:
        names = list(settings.TAXONOMIES) + ["nsf_programs"]
    else:
        names = list(settings.TAXONOMIES) + ["nsf_programs"]

    for name in names:
        p = merge_for_taxonomy(name, delete_auto=args.delete_auto)
        if p:
            print(f"[ok] merged synonyms → {p}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

