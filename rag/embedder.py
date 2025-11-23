from __future__ import annotations

import os
from typing import Iterable, List

from dotenv import load_dotenv

load_dotenv()


def embed_texts(texts: Iterable[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    """
    Generate embeddings with OpenAI if API key exists; otherwise return
    deterministic zero vectors (for local/dev wiring).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    texts = list(texts)
    if not api_key:
        # fallback: zero vectors (384 dims) to keep pipeline runnable
        return [[0.0] * 384 for _ in texts]

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        resp = client.embeddings.create(model=model, input=texts)
        return [d.embedding for d in resp.data]
    except Exception:
        # If API blocked in environment, degrade gracefully
        return [[0.0] * 384 for _ in texts]

