"""
Embedding utilities and semantic matcher.

Provides:
  - embed_text: get an embedding vector via OpenAI
  - embed_canonical_tags: build and save embeddings for a tag list
  - cosine_similarity: compute cosine similarity
  - match_phrase_to_tag: match a phrase to the best taxonomy tag

Environment:
  Requires OPENAI_API_KEY (e.g., in a local .env file).
  Model is configured via settings (OPENAI_EMBEDDING_MODEL).
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, Tuple
from openai import OpenAI
from common.config import settings

# Lazy-initialize OpenAI client to avoid import-time failures in offline tasks
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def load_taxonomy_embeddings(path: str) -> dict:
    """Load or initialize embeddings for canonical taxonomy tags."""
    taxonomy_path = Path(path)
    if taxonomy_path.exists():
        with open(taxonomy_path, "r") as f:
            return json.load(f)
    return {}


def save_taxonomy_embeddings(path: str, data: dict):
    path = Path(path)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# Simple in-memory cache to avoid recomputing embeddings for the same (model, phrase)
_PHRASE_EMBED_CACHE: Dict[Tuple[str, str], np.ndarray] = {}


def embed_text(text: str) -> np.ndarray:
    """Generate an embedding for a given piece of text using OpenAI embeddings."""
    model = settings.OPENAI_EMBEDDING_MODEL
    key = (model, text)
    cached = _PHRASE_EMBED_CACHE.get(key)
    if cached is not None:
        return cached
    response = _get_client().embeddings.create(model=model, input=text)
    embedding = np.array(response.data[0].embedding, dtype=float)
    _PHRASE_EMBED_CACHE[key] = embedding
    return embedding


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    denom = (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    if denom == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / denom)


def embed_canonical_tags(tag_list: list, output_path: str):
    """Create embeddings for a list of canonical tags and save them."""
    embeddings = {}
    for tag in tag_list:
        embeddings[tag] = embed_text(tag).tolist()
    save_taxonomy_embeddings(output_path, embeddings)


def match_phrase_to_tag(phrase: str, taxonomy_embeddings: dict) -> tuple:
    """Given an extracted phrase and taxonomy embeddings, return (best_tag, score)."""
    phrase_vec = embed_text(phrase)
    best_tag = None
    best_score = -1
    for tag, emb in taxonomy_embeddings.items():
        score = cosine_similarity(phrase_vec, np.array(emb, dtype=float))
        if score > best_score:
            best_score = score
            best_tag = tag
    return best_tag, float(best_score)


def top_k_matches(phrase: str, taxonomy_embeddings: dict, k: int = 5) -> list:
    """Return the top-k (tag, score) matches for a phrase against taxonomy embeddings."""
    if k <= 0:
        k = 1
    phrase_vec = embed_text(phrase)
    scored = []
    for tag, emb in taxonomy_embeddings.items():
        score = cosine_similarity(phrase_vec, np.array(emb, dtype=float))
        scored.append((tag, float(score)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]

