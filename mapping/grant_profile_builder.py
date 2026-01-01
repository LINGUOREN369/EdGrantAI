"""Grant profile builder (extraction → mapping → profile JSON)."""

import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Optional
import argparse
import time

from extraction.cke import run_cke
from mapping.canonical_mapper import map_all_taxonomies
from extraction.section_utils import assign_sections_to_phrases
from common.config import settings
from extraction.deadline_extractor import extract_deadline_info


OUTPUT_DIR = settings.PROCESSED_GRANTS_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCHEMA_VERSION_PATH = settings.SCHEMA_VERSION_PATH


def load_taxonomy_version() -> str:
    if SCHEMA_VERSION_PATH.exists():
        with open(SCHEMA_VERSION_PATH, "r") as f:
            data = json.load(f)
            return data.get("taxonomy_version", "0.0.0")
    return "0.0.0"


def build_grant_profile(
    grant_id: str,
    grant_text: str,
    *,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Dict:
    extracted_phrases = run_cke(grant_text)
    phrases_structured = assign_sections_to_phrases(extracted_phrases, grant_text)
    doc_title: Optional[str] = None
    for line in grant_text.splitlines():
        l = line.strip()
        if not l:
            continue
        if l.lower().startswith("title:"):
            try:
                doc_title = l.split(":", 1)[1].strip() or None
            except Exception:
                doc_title = None
            break
    mapped_tags = map_all_taxonomies(
        extracted_phrases,
        phrases_structured,
        doc_title=doc_title,
        full_text=grant_text,
    )
    version = load_taxonomy_version()
    profile = {
        "grant_id": grant_id,
        "created_at": datetime.now(ZoneInfo(settings.TIMEZONE)).isoformat(),
        "taxonomy_version": version,
        "extracted_phrases": extracted_phrases,
        "extracted_phrases_structured": phrases_structured,
        "canonical_tags": mapped_tags,
        "deadline": extract_deadline_info(grant_text),
        "source": {
            "path": str(source_path) if source_path else None,
            "url": str(source_url) if source_url else None,
        },
        "document_title": doc_title,
    }
    return profile


def save_grant_profile(profile: Dict) -> Path:
    grant_id = profile.get("grant_id", "unknown_grant")
    output_path = OUTPUT_DIR / f"{grant_id}_profile.json"
    with open(output_path, "w") as f:
        json.dump(profile, f, indent=2)
    return output_path


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


def _main(argv=None) -> int:
    global OUTPUT_DIR
    parser = argparse.ArgumentParser(description="Build a grant profile JSON from a plain text file.")
    parser.add_argument("input", nargs="?", help="Path to a text file with grant/RFP text")
    parser.add_argument("-g", "--grant-id", help="Identifier for output filename; defaults to filename stem.")
    parser.add_argument("-o", "--out-dir", help=f"Output directory for the profile (default: {OUTPUT_DIR})")
    parser.add_argument("--source-url", help="Optional source URL stored in profile metadata.")
    parser.add_argument("-all", "-a", "--all", action="store_true", help="Process all grant text files in --dir (default: data/grants).")
    parser.add_argument("--dir", default=str((settings.REPO_ROOT / "data" / "grants").resolve()), help="Directory when using --all.")
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
        total_ok = 0
        total_fail = 0
        t_start = time.time()
        for f in files:
            try:
                gid = args.grant_id or f.stem
                text = f.read_text(encoding="utf-8")
                s_url = args.source_url
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

