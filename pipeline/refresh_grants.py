"""
One-shot convenience wrapper to rebuild data/grants/ from a CSV with
recommended settings:

- Overwrite existing .txt files
- Prune filtered rows (non-grants or missing sections)
- Require all four sections (I–IV) to be present on the solicitation page

Usage:
  python -m pipeline.refresh_grants [--csv PATH] [--out-dir DIR]

Defaults:
  CSV auto-detected (prefers data/NSF_database/nsf_funding.csv)
  out-dir = data/grants
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from .build_grants_from_csv import process_csv, _resolve_csv_path
from .config import settings


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Refresh grant text files from CSV with filtering + section extraction")
    p.add_argument("--csv", help="Path to CSV file (auto-detected if omitted)")
    p.add_argument("--out-dir", default=str((settings.REPO_ROOT / "data" / "grants").resolve()), help="Output directory")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    try:
        csv_path = _resolve_csv_path(args.csv)
    except Exception as e:
        print(f"[error] {e}")
        return 2
    out_dir = Path(args.out_dir)

    total, written = process_csv(
        csv_path,
        out_dir,
        fetch=True,
        overwrite=True,
        prune_skipped=True,
        require_all_sections=True,
    )
    print(f"[done] processed {total} rows → wrote {written} files to {out_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

