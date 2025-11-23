from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

from .chunker import chunk_text, make_docs
from .embedder import embed_texts
from .vector_store import ChromaVectorStore

load_dotenv()

STRUCT_DIR = Path(os.getenv("DATA_STRUCTURED_DIR", "./data/structured"))


def _load_structured(fp: Path) -> Dict:
    return json.loads(fp.read_text(encoding="utf-8"))


def build_index():
    store = ChromaVectorStore()
    ids: List[str] = []
    texts: List[str] = []
    metas: List[Dict] = []

    for f in sorted(STRUCT_DIR.glob("*.json")):
        data = _load_structured(f)
        grant_id = data["id"]
        base_meta = {
            "grant_id": grant_id,
            "title": data.get("title"),
            "funder": data.get("funder"),
        }

        raw_text = (data.get("summary") or "")
        for tag in data.get("tags", []) or []:
            base_meta.setdefault("tags", []).append(tag)

        chunks = chunk_text(raw_text or "") or [raw_text or data.get("title", "")]
        docs = make_docs(chunks, base_meta)
        for d in docs:
            ids.append(f"{grant_id}:{d['metadata']['chunk_id']}")
            texts.append(d["text"])
            metas.append(d["metadata"])

    if not texts:
        print("No structured summaries to index.")
        return

    embs = embed_texts(texts)
    store.upsert(ids=ids, texts=texts, metadatas=metas, embeddings=embs)
    print(f"Indexed {len(texts)} chunks → collection '{store.collection_name}'")


if __name__ == "__main__":
    build_index()

