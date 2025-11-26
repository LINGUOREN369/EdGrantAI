"""
Build taxonomy embeddings only.

This script computes OpenAI embeddings for the taxonomy tag lists and writes
them to `data/taxonomy/embeddings/<name>_embeddings.json`.

Usage examples:
  - python -m pipeline.build_taxonomy_embeddings --all
  - python -m pipeline.build_taxonomy_embeddings --names mission_tags population_tags
  - python -m pipeline.build_taxonomy_embeddings --all --force

Environment:
  Requires OPENAI_API_KEY to be set (e.g., in a local .env file).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from .embedding_matcher import embed_canonical_tags
from .config import settings


EMBEDDINGS_DIR = settings.TAXONOMY_EMBEDDINGS_DIR
DEFAULT_TAXONOMIES = [
    "mission_tags",
    "population_tags",
    "org_types",
    "geography_tags",
    "red_flag_tags",
]


def load_taxonomy_list(name: str) -> List[str]:
    path = settings.TAXONOMY_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {path}")
    with open(path, "r") as f:
        return json.load(f)


def build_for_name(name: str, force: bool = False) -> Path:
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EMBEDDINGS_DIR / f"{name}_embeddings.json"

    if out_path.exists() and not force:
        print(f"[skip] {name}: embeddings already exist at {out_path}")
        return out_path

    tags = load_taxonomy_list(name)
    print(f"[build] {name}: {len(tags)} tags → {out_path}")
    embed_canonical_tags(tags, str(out_path))
    print(f"[done]  {name}: saved {out_path}")
    return out_path


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute and save taxonomy embeddings only."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--all",
        action="store_true",
        help="Build embeddings for all default taxonomy files.",
    )
    group.add_argument(
        "--names",
        nargs="+",
        metavar="NAME",
        help="Specific taxonomy names to build (e.g., mission_tags population_tags).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even if an embeddings file already exists.",
    )

    args = parser.parse_args(argv)

    names = args.names if args.names else ([] if not args.all else DEFAULT_TAXONOMIES)
    if not names:
        # Default to all if nothing provided
        names = DEFAULT_TAXONOMIES

    # Validate and build
    for name in names:
        if name not in DEFAULT_TAXONOMIES:
            print(f"[warn] Unrecognized taxonomy '{name}'. Attempting anyway…")
        try:
            build_for_name(name, force=args.force)
        except FileNotFoundError as e:
            print(f"[error] {e}")
            return 1
        except Exception as e:
            print(f"[error] Failed to build embeddings for '{name}': {e}")
            return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
