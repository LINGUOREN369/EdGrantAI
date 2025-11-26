"""
Embedding utilities and semantic matcher.

Provides:
  - embed_text: get an embedding vector via OpenAI
  - embed_canonical_tags: build and save embeddings for a tag list
  - cosine_similarity: compute cosine similarity
  - match_phrase_to_tag: match a phrase to the best taxonomy tag

Usage examples:
  - from pipeline.embedding_matcher import embed_canonical_tags
    embed_canonical_tags(["literacy", "STEM"], "data/taxonomy/embeddings/example.json")
  - from pipeline.embedding_matcher import match_phrase_to_tag
    best_tag, score = match_phrase_to_tag("robotics clubs", {"robotics_education": [0.0, ...]})

Environment:
  Requires OPENAI_API_KEY (e.g., in a local .env file).
  Uses model: text-embedding-3-small.
"""

import json
import numpy as np
from openai import OpenAI
from pathlib import Path
from .config import settings

# Eagerly initialize the client so missing keys fail at import time
client = OpenAI()


def load_taxonomy_embeddings(path: str) -> dict:
    """
    Load or initialize embeddings for canonical taxonomy tags.
    Expecting a JSON mapping: {"tag": embedding_vector}
    """
    taxonomy_path = Path(path)
    if taxonomy_path.exists():
        with open(taxonomy_path, "r") as f:
            return json.load(f)
    return {}


def save_taxonomy_embeddings(path: str, data: dict):
    path = Path(path)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def embed_text(text: str) -> np.ndarray:
    """
    Generate an embedding for a given piece of text using OpenAI embeddings.
    Returns a numpy array.
    """
    response = client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=text
    )
    embedding = response.data[0].embedding
    return np.array(embedding, dtype=float)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    denom = (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    if denom == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / denom)


def embed_canonical_tags(tag_list: list, output_path: str):
    """
    Create embeddings for a list of canonical tags and save them.
    """
    embeddings = {}
    for tag in tag_list:
        embeddings[tag] = embed_text(tag).tolist()
    save_taxonomy_embeddings(output_path, embeddings)


def match_phrase_to_tag(phrase: str, taxonomy_embeddings: dict) -> tuple:
    """
    Given an extracted phrase and taxonomy embeddings,
    compute similarity against all canonical tags.

    Returns (best_tag, best_score)
    """
    phrase_vec = embed_text(phrase)

    best_tag = None
    best_score = -1

    for tag, emb in taxonomy_embeddings.items():
        tag_vec = np.array(emb, dtype=float)
        score = cosine_similarity(phrase_vec, tag_vec)
        if score > best_score:
            best_score = score
            best_tag = tag

    return best_tag, float(best_score)
