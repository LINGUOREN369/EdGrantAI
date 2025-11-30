"""
Organization profile builder.

Runs the end-to-end pipeline on organization text:
  1) Controlled Keyphrase Extraction (CKE)
  2) Canonical mapping across taxonomies
  3) Attach taxonomy version and metadata
  4) Save profile (optional)

Python usage:
  - from pipeline.org_profile_builder import process_org
    path = process_org("org_0001", "Organization mission text here.")

CLI:
  - Build taxonomy embeddings first (once):
      - python -m pipeline.build_taxonomy_embeddings --all
  - Build a profile from a text file:
      - Derive id from filename:
          - python -m pipeline.org_profile_builder data/orgs/org_0001.txt
      - Specify id and output directory:
          - python -m pipeline.org_profile_builder data/orgs/org_0001.txt --org-id org_0001 --out-dir data/processed_orgs
      - Optionally include a source URL:
          - python -m pipeline.org_profile_builder data/orgs/org_0001.txt --source-url https://example.org/about
      - Convenience: if the first non-empty line of the text file is an http(s) URL, it is used as the source URL and omitted from the processed text.
  - Process all .txt org files in a directory (default: data/orgs):
      - python -m pipeline.org_profile_builder --all
      - Custom directory/extension/output:
          - python -m pipeline.org_profile_builder --all --dir data/orgs --ext .txt --out-dir data/processed_orgs
  - Output:
      - data/processed_orgs/org_0001_profile.json (includes source.path and optional source.url)

Environment:
  Requires OPENAI_API_KEY and taxonomy assets in data/taxonomy/.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from zoneinfo import ZoneInfo

from .cke import run_cke
from .canonical_mapper import map_all_taxonomies
from .config import settings


OUTPUT_DIR = settings.PROCESSED_ORGS_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCHEMA_VERSION_PATH = settings.SCHEMA_VERSION_PATH


def load_taxonomy_version() -> str:
    if SCHEMA_VERSION_PATH.exists():
        with open(SCHEMA_VERSION_PATH, "r") as f:
            data = json.load(f)
            return data.get("taxonomy_version", "0.0.0")
    return "0.0.0"


def build_org_profile(
    org_id: str,
    org_text: str,
    *,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Dict:
    """
    Full pipeline for organization text.
    1. Extract keyphrases via CKE
    2. Map phrases to canonical tags
    3. Attach taxonomy version & metadata
    4. Produce final org profile
    """

    extracted_phrases = run_cke(org_text)
    mapped_tags = map_all_taxonomies(extracted_phrases)
    version = load_taxonomy_version()

    profile = {
        "org_id": org_id,
        "created_at": datetime.now(ZoneInfo(settings.TIMEZONE)).isoformat(),
        "taxonomy_version": version,
        "extracted_phrases": extracted_phrases,
        "canonical_tags": mapped_tags,
        "source": {
            "path": str(source_path) if source_path else None,
            "url": str(source_url) if source_url else None,
        },
    }
    return profile


def save_org_profile(profile: Dict) -> Path:
    org_id = profile.get("org_id", "unknown_org")
    output_path = OUTPUT_DIR / f"{org_id}_profile.json"
    with open(output_path, "w") as f:
        json.dump(profile, f, indent=2)
    return output_path


def process_org(
    org_id: str,
    org_text: str,
    *,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Path:
    profile = build_org_profile(org_id, org_text, source_path=source_path, source_url=source_url)
    return save_org_profile(profile)


def _main(argv=None) -> int:
    global OUTPUT_DIR
    parser = argparse.ArgumentParser(description="Build an organization profile JSON from a plain text file.")
    parser.add_argument("input", nargs="?", help="Path to an org text file (e.g., data/orgs/org_0001.txt)")
    parser.add_argument("-o", "--org-id", help="ID for output filename; defaults to input filename stem.")
    parser.add_argument("--out-dir", help=f"Output directory (default: {OUTPUT_DIR})")
    parser.add_argument("--source-url", help="Optional source URL (stored in profile metadata).")
    parser.add_argument("-all", "-a", "--all", action="store_true", help="Process all text files in --dir (default: data/orgs).")
    parser.add_argument("--dir", default=str((settings.REPO_ROOT / "data" / "orgs").resolve()), help="Directory when using --all.")
    parser.add_argument("--ext", default=".txt", help="File extension to include when using --all (default: .txt).")

    args = parser.parse_args(argv)

    if args.all:
        dir_path = Path(args.dir)
        if not dir_path.exists() or not dir_path.is_dir():
            print(f"[error] Directory not found: {dir_path}")
            return 1
        files = sorted(p for p in dir_path.glob(f"*{args.ext}") if p.is_file())
        if not files:
            print(f"[warn] No files found in {dir_path} matching *{args.ext}")
            return 0
        if args.out_dir:
            OUTPUT_DIR = Path(args.out_dir)
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        ok = 0
        fail = 0
        t_start = time.time()
        for f in files:
            try:
                oid = args.org_id or f.stem
                text = f.read_text(encoding="utf-8")
                s_url = args.source_url
                # First non-empty line URL convenience
                if not s_url:
                    lines = text.splitlines()
                    for idx, raw in enumerate(lines):
                        line = raw.strip()
                        if not line:
                            continue
                        if line.startswith("http://") or line.startswith("https://"):
                            s_url = line
                            del lines[idx]
                            text = "\n".join(lines).lstrip("\n")
                        break
                t0 = time.time()
                out = process_org(oid, text, source_path=str(f), source_url=s_url)
                dt = time.time() - t0
                print(f"[ok] {f.name} → {out.name} ({dt:.2f}s)")
                ok += 1
            except Exception as e:
                print(f"[error] {f.name}: {e}")
                fail += 1
        total = time.time() - t_start
        print(f"[done] processed: {ok} ok, {fail} failed in {total:.2f}s")
        return 0 if fail == 0 else 1

    # Single-file mode
    if not args.input:
        parser.print_usage()
        return 2
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[error] Input file not found: {in_path}")
        return 1
    org_id = args.org_id or in_path.stem
    org_text = in_path.read_text(encoding="utf-8")
    source_url = args.source_url
    if not source_url:
        lines = org_text.splitlines()
        for idx, raw in enumerate(lines):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("http://") or line.startswith("https://"):
                source_url = line
                del lines[idx]
                org_text = "\n".join(lines).lstrip("\n")
            break
    if args.out_dir:
        OUTPUT_DIR = Path(args.out_dir)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        t0 = time.time()
        out = process_org(org_id, org_text, source_path=str(in_path), source_url=source_url)
        dt = time.time() - t0
        print(f"[ok] Saved profile → {out}  ({dt:.2f}s)")
        return 0
    except Exception as e:
        print(f"[error] Failed to build org profile: {e}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())

