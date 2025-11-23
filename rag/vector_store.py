from __future__ import annotations

import os
from typing import Dict, Iterable, List, Optional

from dotenv import load_dotenv

load_dotenv()


class ChromaVectorStore:
    def __init__(self, collection: Optional[str] = None, persist_dir: Optional[str] = None):
        import chromadb
        from chromadb.config import Settings

        self.persist_dir = persist_dir or os.getenv("CHROMA_DB_DIR", "./data/embeddings/chroma")
        self.collection_name = collection or os.getenv("VECTOR_COLLECTION", "grants")

        self.client = chromadb.PersistentClient(path=self.persist_dir, settings=Settings(is_persistent=True))
        self.col = self.client.get_or_create_collection(self.collection_name)

    def upsert(self, ids: List[str], texts: List[str], metadatas: Optional[List[Dict]] = None, embeddings: Optional[List[List[float]]] = None):
        self.col.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)

    def query(self, query_texts: List[str], n_results: int = 5, where: Optional[Dict] = None):
        return self.col.query(query_texts=query_texts, n_results=n_results, where=where)

