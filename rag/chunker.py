from __future__ import annotations

from typing import Dict, Iterable, List


def paragraphs(text: str) -> List[str]:
    parts = [p.strip() for p in text.split("\n\n")]
    return [p for p in parts if p]


def chunk_text(text: str, max_chars: int = 1200) -> List[str]:
    chunks: List[str] = []
    buf: List[str] = []
    size = 0
    for p in paragraphs(text):
        if size + len(p) + 2 > max_chars and buf:
            chunks.append("\n\n".join(buf))
            buf, size = [], 0
        buf.append(p)
        size += len(p) + 2
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def make_docs(chunks: Iterable[str], base_metadata: Dict) -> List[Dict]:
    docs = []
    for i, ch in enumerate(chunks):
        m = dict(base_metadata)
        m.update({"chunk_id": i})
        docs.append({"text": ch, "metadata": m})
    return docs

