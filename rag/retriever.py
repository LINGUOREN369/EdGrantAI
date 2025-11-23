from __future__ import annotations

from typing import Dict, List, Optional

from .vector_store import ChromaVectorStore
from .embedder import embed_texts


class SmartRetriever:
    """
    Metadata-filtered retrieval with fallback to pure semantic retrieval.
    """

    def __init__(self, store: Optional[ChromaVectorStore] = None):
        self.store = store or ChromaVectorStore()

    def retrieve(self, query: str, n_results: int = 5, filters: Optional[Dict] = None) -> Dict:
        # First try metadata-filtered retrieval
        where = filters or None
        res = self.store.query([query], n_results=n_results, where=where)
        if not res or not res.get("ids") or not res["ids"][0]:
            # Fallback: pure semantic retrieval
            res = self.store.query([query], n_results=n_results)
        return res

