"""
Build taxonomy embeddings only.

Computes embeddings for taxonomy tag lists and writes them to
data/taxonomy/embeddings/<name>_embeddings.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from mapping.embedding_matcher import embed_canonical_tags
from common.config import settings


EMBEDDINGS_DIR = settings.TAXONOMY_EMBEDDINGS_DIR


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
    parser = argparse.ArgumentParser(description="Compute and save taxonomy embeddings only.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Build embeddings for all default taxonomy files.")
    group.add_argument("--names", nargs="+", metavar="NAME", help="Specific taxonomy names to build.")
    parser.add_argument("--force", action="store_true", help="Rebuild even if an embeddings file already exists.")
    args = parser.parse_args(argv)

    names = args.names if args.names else ([] if not args.all else settings.TAXONOMIES)
    if not names:
        names = settings.TAXONOMIES
    for name in names:
        if name not in settings.TAXONOMIES:
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

