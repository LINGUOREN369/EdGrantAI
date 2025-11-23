from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from .llm_structured import extract_structured, save_schema_json

load_dotenv()

RAW_DIR = Path(os.getenv("DATA_RAW_DIR", "./data/raw"))
STRUCT_DIR = Path(os.getenv("DATA_STRUCTURED_DIR", "./data/structured"))


def build_all():
    STRUCT_DIR.mkdir(parents=True, exist_ok=True)
    for fp in sorted(RAW_DIR.glob("*.txt")):
        text = fp.read_text(encoding="utf-8")
        schema = extract_structured(text, url=None)
        out = STRUCT_DIR / f"{schema.id}.json"
        save_schema_json(schema, out)
        print(f"Structured → {out}")


if __name__ == "__main__":
    build_all()

