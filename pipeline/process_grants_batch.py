"""
Process grant .txt files in batches to build profiles.

Selects the next N unprocessed grant text files under data/grants/ and builds
their profiles into data/processed_grants/ using the existing pipeline.

Behavior
- Skips any grant that already has a corresponding `_profile.json` file.
- For each text file, if the first non-empty line is an http(s) URL, it is used
  as `source_url` and omitted from the processed text (same behavior as the CLI).

CLI examples
- python -m pipeline.process_grants_batch --count 20
- python -m pipeline.process_grants_batch --dir data/grants --count 10 --dry-run
"""

from __future__ import annotations

import argparse
from pathlib import Path
import random
from typing import List, Optional, Tuple
import time

from .config import settings
from .grant_profile_builder import build_grant_profile, save_grant_profile


def _read_text_and_source_url(path: Path) -> Tuple[str, Optional[str]]:
    text = path.read_text(encoding="utf-8")
    source_url: Optional[str] = None
    lines = text.splitlines()
    for idx, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("http://") or line.startswith("https://"):
            source_url = line
            del lines[idx]
            text = "\n".join(lines).lstrip("\n")
        break
    return text, source_url


def collect_pending(dir_path: Path, ext: str = ".txt", *, force: bool = False) -> List[Path]:
    grants = sorted(p for p in dir_path.glob(f"*{ext}") if p.is_file())
    if force:
        return grants
    pending: List[Path] = []
    out_dir = settings.PROCESSED_GRANTS_DIR
    for g in grants:
        stem = g.stem
        out_path = out_dir / f"{stem}_profile.json"
        if not out_path.exists():
            pending.append(g)
    return pending


def _is_k12_related(profile: dict, raw_text: str) -> bool:
    """Heuristic K–12 detector using canonical tags, extracted phrases, and raw text.

    Returns True if the grant appears related to K–12 education (students or teachers).
    """
    text = (raw_text or "").lower()
    # Quick keyword scan in raw text
    kw = [
        "k-12", "k–12", "k12", "pk-12", "prek-12", "pre-k", "prekindergarten",
        "elementary", "middle school", "high school", "secondary school", "secondary education",
        "school district", "districts", "local education agency", "lea", "teacher professional development",
    ]
    if any(k in text for k in kw):
        return True

    # Check extracted phrases
    for ph in profile.get("extracted_phrases", []) or []:
        s = str(ph).lower()
        if any(k in s for k in kw):
            return True

    # Check canonical tags
    cats = profile.get("canonical_tags", {}) or {}
    for k in ("mission_tags", "population_tags", "org_type_tags", "geography_tags", "red_flag_tags"):
        for d in cats.get(k, []) or []:
            tag = (d.get("tag") or "").lower()
            if any(key in tag for key in kw):
                return True
    return False


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build next N grant profiles from data/grants/ (skips existing).")
    p.add_argument("--dir", default=str((settings.REPO_ROOT / "data" / "grants").resolve()), help="Directory of grant .txt files")
    p.add_argument("--ext", default=".txt", help="Grant file extension (default .txt)")
    p.add_argument("--count", type=int, default=20, help="Number of pending grants to process (default 20)")
    p.add_argument("--dry-run", action="store_true", help="List pending grants without processing")
    p.add_argument("--k12-only", action="store_true", help="Save profiles only for K–12 education‑related grants")
    p.add_argument("--force", action="store_true", help="Rebuild profiles even if they already exist")
    p.add_argument("--random", action="store_true", help="Randomize the order before selecting the next N")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    dir_path = Path(args.dir)
    if not dir_path.exists() or not dir_path.is_dir():
        print(f"[error] Directory not found: {dir_path}")
        return 2
    pending = collect_pending(dir_path, args.ext, force=args.force)
    if args.random:
        random.shuffle(pending)
    if not pending:
        print("[done] No pending grants — everything is processed.")
        return 0

    batch = pending[: max(1, int(args.count))]
    if args.dry_run:
        print(f"[pending] {len(pending)} total; next batch of {len(batch)}:")
        for p in batch:
            print(f"- {p.name}")
        return 0

    total_ok = 0
    total_fail = 0
    t_start = time.time()
    for f in batch:
        try:
            gid = f.stem
            grant_text, source_url = _read_text_and_source_url(f)
            # Build in-memory profile to allow filtering before save
            profile = build_grant_profile(
                gid,
                grant_text,
                source_path=str(f),
                source_url=source_url,
            )
            # Optional K–12 filter
            if args.k12_only and not _is_k12_related(profile, grant_text):
                print(f"[skip] {f.name} — not K–12 education related")
                continue
            out_path = save_grant_profile(profile)
            print(f"[ok] {f.name} → {out_path.name}")
            total_ok += 1
        except Exception as e:
            print(f"[error] {f.name}: {e}")
            total_fail += 1
    dt = time.time() - t_start
    print(f"[done] batch processed: {total_ok} ok, {total_fail} failed in {dt:.2f}s")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
