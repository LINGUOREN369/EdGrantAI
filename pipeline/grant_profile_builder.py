"""
Grant profile builder.

Runs the end-to-end pipeline:
  1) Controlled Keyphrase Extraction (CKE)
  2) Canonical mapping across taxonomies
  3) Attach taxonomy version and metadata
  4) Save profile (optional)

Python usage:
  - from pipeline.grant_profile_builder import process_grant
    path = process_grant("grant_0001", "Grant text here.")

CLI:
  - Build taxonomy embeddings first (once):
      - python -m pipeline.build_taxonomy_embeddings --all
  - Build a grant profile from a text file:
      - Derive id from filename:
          - python -m pipeline.grant_profile_builder data/grants/text_grant_1.txt
      - Specify id and output directory:
          - python -m pipeline.grant_profile_builder data/grants/text_grant_1.txt --grant-id text_grant_1 --out-dir data/processed_grants
      - Optionally include a source URL:
          - python -m pipeline.grant_profile_builder data/grants/text_grant_1.txt --source-url https://example.org/rfp
      - Convenience: if the first non-empty line of the text file is an http(s) URL, it is used as the source URL and omitted from the processed text.
  - Process all .txt grant files in a directory (default: data/grants):
      - python -m pipeline.grant_profile_builder --all
      - Custom directory/extension/output:
          - python -m pipeline.grant_profile_builder --all --dir data/grants --ext .txt --out-dir data/processed_grants
  - Output:
      - data/processed_grants/text_grant_1_profile.json (includes source.path and optional source.url)

Source metadata:
  - The profile records input provenance under `source`:
      - source.path: the local input file path
      - source.url: an optional RFP/source URL when provided via --source-url

Environment:
  Requires OPENAI_API_KEY and taxonomy assets in data/taxonomy/.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from .cke import run_cke
from .canonical_mapper import map_all_taxonomies
from .config import settings
import argparse
import time

# Save location for processed grant profiles
OUTPUT_DIR = settings.PROCESSED_GRANTS_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Path to taxonomy schema version
SCHEMA_VERSION_PATH = settings.SCHEMA_VERSION_PATH


# -------------------------------------------------------------
# Helper: Load taxonomy version
# -------------------------------------------------------------
def load_taxonomy_version() -> str:
    if SCHEMA_VERSION_PATH.exists():
        with open(SCHEMA_VERSION_PATH, "r") as f:
            data = json.load(f)
            return data.get("taxonomy_version", "0.0.0")
    return "0.0.0"


# -------------------------------------------------------------
# Main: Build a full structured grant profile
# -------------------------------------------------------------
def build_grant_profile(
    grant_id: str,
    grant_text: str,
    *,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Dict:
    """
    Full pipeline:
    1. Extract keyphrases via CKE
    2. Map phrases to canonical tags
    3. Attach taxonomy version & metadata
    4. Produce final grant profile
    """

    # Step 1 — Controlled Keyphrase Extraction
    extracted_phrases = run_cke(grant_text)

    # Step 2 — Canonical Mapping
    mapped_tags = map_all_taxonomies(extracted_phrases)

    # Step 3 — Load taxonomy version
    version = load_taxonomy_version()

    # Step 4 — Construct final profile
    profile = {
        "grant_id": grant_id,
        "created_at": datetime.utcnow().isoformat(),
        "taxonomy_version": version,
        "extracted_phrases": extracted_phrases,
        "canonical_tags": mapped_tags,
        "source": {
            "path": str(source_path) if source_path else None,
            "url": str(source_url) if source_url else None,
        },
    }

    return profile


# -------------------------------------------------------------
# Save profile to disk
# -------------------------------------------------------------
def save_grant_profile(profile: Dict) -> Path:
    grant_id = profile.get("grant_id", "unknown_grant")
    output_path = OUTPUT_DIR / f"{grant_id}_profile.json"

    with open(output_path, "w") as f:
        json.dump(profile, f, indent=2)

    return output_path


# -------------------------------------------------------------
# Convenience wrapper: run + save
# -------------------------------------------------------------
def process_grant(
    grant_id: str,
    grant_text: str,
    *,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Path:
    profile = build_grant_profile(
        grant_id,
        grant_text,
        source_path=source_path,
        source_url=source_url,
    )
    return save_grant_profile(profile)


# Example usage (commented for safety)
# if __name__ == "__main__":
#     text = "We support robotics clubs and maker labs for middle school girls."
#     path = process_grant("grant_0001", text)
#     print(f"Profile saved to: {path}")


def _main(argv=None) -> int:
    global OUTPUT_DIR
    parser = argparse.ArgumentParser(
        description="Build a grant profile JSON from a plain text file."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to a text file containing grant/RFP text (e.g., data/grants/text_grant_1.txt)",
    )
    parser.add_argument(
        "-g",
        "--grant-id",
        help="Identifier used in the output filename; default is the input filename stem.",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        help=f"Output directory for the profile (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--source-url",
        help="Optional source URL for the grant/RFP (stored in profile metadata).",
    )
    parser.add_argument(
        "-all", "-a", "--all",
        action="store_true",
        help="Process all grant text files in --dir (default: data/grants).",
    )
    parser.add_argument(
        "--dir",
        default=str((settings.REPO_ROOT / "data" / "grants").resolve()),
        help="Directory to scan when using --all (defaults to data/grants).",
    )
    parser.add_argument(
        "--ext",
        default=".txt",
        help="File extension to include when using --all (default: .txt).",
    )

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

        total_ok = 0
        total_fail = 0
        t_start = time.time()
        for f in files:
            try:
                gid = args.grant_id or f.stem
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
                out_path = process_grant(
                    gid,
                    text,
                    source_path=str(f),
                    source_url=s_url,
                )
                dt = time.time() - t0
                print(f"[ok] {f.name} → {out_path.name} ({dt:.2f}s)")
                total_ok += 1
            except Exception as e:
                print(f"[error] {f.name}: {e}")
                total_fail += 1
        total_dt = time.time() - t_start
        print(f"[done] processed: {total_ok} ok, {total_fail} failed in {total_dt:.2f}s")
        return 0 if total_fail == 0 else 1

    # Single-file mode
    if not args.input:
        parser.print_usage()
        return 2
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[error] Input file not found: {in_path}")
        return 1

    grant_id = args.grant_id or in_path.stem
    grant_text = in_path.read_text(encoding="utf-8")
    source_url = args.source_url

    # If the first non-empty line is an http(s) URL, treat it as source URL
    # and remove it from the grant text to avoid polluting extraction.
    if not source_url:
        lines = grant_text.splitlines()
        for idx, raw in enumerate(lines):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("http://") or line.startswith("https://"):
                source_url = line
                del lines[idx]
                grant_text = "\n".join(lines).lstrip("\n")
            break

    # Optionally override output directory
    if args.out_dir:
        OUTPUT_DIR = Path(args.out_dir)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        t0 = time.time()
        path = process_grant(
            grant_id,
            grant_text,
            source_path=str(in_path),
            source_url=source_url,
        )
        dt = time.time() - t0
        print(f"[ok] Saved profile → {path}  ({dt:.2f}s)")
        return 0
    except Exception as e:
        print(f"[error] Failed to build profile: {e}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
