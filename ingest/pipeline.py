from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .fetch_html import fetch_html
from .parse_pdf import pdf_to_text
from .clean_text import basic_clean

load_dotenv()


RAW_DIR = Path(os.getenv("DATA_RAW_DIR", "./data/raw"))


def _slugify(s: str) -> str:
    s = s.strip().lower()
    h = hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]
    return h


def ingest_source(source: str, kind: Optional[str] = None, filename: Optional[str] = None) -> Path:
    """
    Ingest a single source (URL or local file), clean text, and store into data/raw.
    - If source endswith .pdf (or kind==pdf) → parse PDF
    - If source is http(s) → fetch HTML and keep text content (raw HTML by default)
    - Else → treat as local text
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    content: str
    if kind == "pdf" or source.lower().endswith(".pdf"):
        content = pdf_to_text(source)
    elif source.startswith("http://") or source.startswith("https://"):
        content = fetch_html(source)
    else:
        content = Path(source).read_text(encoding="utf-8")

    cleaned = basic_clean(content)
    stem = filename or _slugify(source)
    out_path = RAW_DIR / f"{stem}.txt"
    out_path.write_text(cleaned, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Simple ingestion pipeline → data/raw")
    ap.add_argument("source", help="URL or local path (.pdf/.txt)")
    ap.add_argument("--kind", choices=["pdf", "html", "auto"], default="auto")
    ap.add_argument("--name", default=None, help="Optional output filename stem")
    args = ap.parse_args()

    kind = None if args.kind == "auto" else args.kind
    out = ingest_source(args.source, kind=kind, filename=args.name)
    print(f"Wrote raw text → {out}")

