from __future__ import annotations

from typing import Dict, List

from rag.retriever import SmartRetriever
from .scoring import weighted_score


class MatchEngine:
    def __init__(self):
        self.retriever = SmartRetriever()

    def match(self, project_description: str, top_k: int = 5) -> List[Dict]:
        res = self.retriever.retrieve(project_description, n_results=top_k)
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances") or res.get("embeddings") or None

        # Chroma returns distances when using Euclidean/cosine. If absent, fallback to rank.
        base_sims = []
        if dists and dists[0]:
            # convert distance to similarity-ish
            for d in dists[0]:
                try:
                    sim = 1.0 / (1.0 + float(d))
                except Exception:
                    sim = 0.5
                base_sims.append(sim)
        else:
            base_sims = [1.0 - i * 0.05 for i in range(len(ids))]

        project = {"profile": project_description}
        results = []
        for _id, _doc, _meta, _sim in zip(ids, docs, metas, base_sims):
            score = weighted_score(_sim, _meta or {}, project)
            results.append({
                "chunk_id": _id,
                "grant_id": (_meta or {}).get("grant_id"),
                "title": (_meta or {}).get("title"),
                "snippet": _doc[:400],
                "score": round(score, 4),
                "meta": _meta or {},
            })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

