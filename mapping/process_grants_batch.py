"""Process next N grant profiles from data/grants, skipping existing ones."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional
import time

from common.config import settings
from mapping.grant_profile_builder import process_grant


def _first_url_strip(text: str) -> tuple[str, Optional[str]]:
    lines = text.splitlines()
    url = None
    for idx, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("http://") or line.startswith("https://"):
            url = line
            del lines[idx]
            text = "\n".join(lines).lstrip("\n")
        break
    return text, url


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build next N grant profiles from data/grants, skipping existing JSONs.")
    p.add_argument("--grants-dir", default=str((settings.REPO_ROOT / "data" / "grants").resolve()), help="Source grants text dir")
    p.add_argument("--out-dir", default=str(settings.PROCESSED_GRANTS_DIR.resolve()), help="Output processed_grants dir")
    p.add_argument("--count", type=int, default=20, help="Number of new profiles to build (default 20)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    grants_dir = Path(args.grants_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    picked = 0
    t_start = time.time()
    for fp in sorted(grants_dir.glob("*.txt")):
        gid = fp.stem
        out_json = out_dir / f"{gid}_profile.json"
        if out_json.exists():
            continue
        text = fp.read_text(encoding="utf-8")
        text, url = _first_url_strip(text)
        t0 = time.time()
        try:
            path = process_grant(gid, text, source_path=str(fp), source_url=url)
            dt = time.time() - t0
            print(f"[ok] {fp.name} → {path.name} ({dt:.2f}s)")
            picked += 1
        except Exception as e:
            print(f"[error] {fp.name}: {e}")
        if picked >= max(1, int(args.count)):
            break
    total_dt = time.time() - t_start
    print(f"[done] built {picked} profiles in {total_dt:.2f}s into {out_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

