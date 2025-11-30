"""
Validate taxonomy lists and their embeddings are in sync.

Checks per taxonomy:
- Count of tags in taxonomy JSON
- Count of embeddings in embeddings JSON
- Missing embeddings (tags without vectors)
- Extra embeddings (vectors for tags not in taxonomy)
- Embedding vector length consistency

Usage:
  - python -m pipeline.validate_taxonomy --all
  - python -m pipeline.validate_taxonomy --names mission_tags population_tags

Exit codes:
  - 0 when no issues found (or only warnings without --strict)
  - 1 when issues found and --strict is set
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

from .config import settings


def _load_json(path: Path):
    with open(path, "r") as f:
        return json.load(f)


def validate_taxonomy(name: str) -> Tuple[bool, str]:
    tax_path = settings.TAXONOMY_DIR / f"{name}.json"
    emb_path = settings.TAXONOMY_EMBEDDINGS_DIR / f"{name}_embeddings.json"

    if not tax_path.exists():
        return False, f"[error] taxonomy missing: {tax_path}"
    if not emb_path.exists():
        return False, f"[error] embeddings missing: {emb_path}"

    tags: List[str] = _load_json(tax_path)
    embs: Dict[str, List[float]] = _load_json(emb_path)

    tag_set = set(tags)
    emb_set = set(embs.keys())

    missing = sorted(tag_set - emb_set)
    extra = sorted(emb_set - tag_set)

    # Vector length checks
    vec_len = None
    bad_vecs = []
    for k, v in embs.items():
        if not isinstance(v, list) or not v:
            bad_vecs.append(k)
            continue
        if vec_len is None:
            vec_len = len(v)
        elif len(v) != vec_len:
            bad_vecs.append(k)

    lines = []
    lines.append(f"[ok] taxonomy: {name}")
    lines.append(f"  - tags: {len(tags)}  embeddings: {len(embs)}")
    if vec_len is not None:
        lines.append(f"  - embedding_dim: {vec_len}")
    if missing:
        lines.append(f"  - missing embeddings: {len(missing)}")
        for m in missing[:10]:
            lines.append(f"      • {m}")
        if len(missing) > 10:
            lines.append(f"      • … {len(missing)-10} more")
    if extra:
        lines.append(f"  - extra embeddings: {len(extra)}")
        for e in extra[:10]:
            lines.append(f"      • {e}")
        if len(extra) > 10:
            lines.append(f"      • … {len(extra)-10} more")
    if bad_vecs:
        lines.append(f"  - malformed vectors: {len(bad_vecs)} (inconsistent length or empty)")

    ok = not (missing or bad_vecs)
    return ok, "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate taxonomy and embeddings alignment.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Validate all configured taxonomies.")
    group.add_argument("--names", nargs="+", metavar="NAME", help="Specific taxonomy names to validate.")
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero code on any issues.")

    args = parser.parse_args(argv)

    names = args.names if args.names else ([] if not args.all else settings.TAXONOMIES)
    if not names:
        names = settings.TAXONOMIES

    overall_ok = True
    print(f"Schema version: {_load_json(settings.SCHEMA_VERSION_PATH).get('taxonomy_version', 'unknown')}")
    for name in names:
        ok, report = validate_taxonomy(name)
        print(report)
        overall_ok = overall_ok and ok

    if args.strict and not overall_ok:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

