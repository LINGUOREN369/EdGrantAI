"""
Canonical taxonomy mapper.

Maps extracted phrases to canonical taxonomy tags using precomputed taxonomy
embeddings and semantic similarity.

Usage examples:
  - from pipeline.canonical_mapper import map_all_taxonomies
    tags = map_all_taxonomies(["robotics clubs", "middle school girls"])

Data locations:
  - Taxonomies: data/taxonomy/*.json
  - Embeddings: data/taxonomy/embeddings/*_embeddings.json

Environment:
  Requires OPENAI_API_KEY (phrase embeddings are computed at match time).
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from .embedding_matcher import match_phrase_to_tag, load_taxonomy_embeddings
from .config import settings


# -------------------------------------------------------------
# Helper: Load canonical taxonomy tag lists
# -------------------------------------------------------------
def load_taxonomy_list(name: str) -> List[str]:
    """
    Load a taxonomy JSON array such as:
    mission_tags.json, population_tags.json, etc.
    """
    path = settings.TAXONOMY_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {path}")
    with open(path, "r") as f:
        return json.load(f)


# -------------------------------------------------------------
# Helper: Load taxonomy embeddings (precomputed)
# -------------------------------------------------------------
def load_embeddings(name: str) -> Dict[str, List[float]]:
    """
    Load precomputed embeddings for a taxonomy list.
    Expects files like mission_tags_embeddings.json
    """
    path = settings.TAXONOMY_EMBEDDINGS_DIR / f"{name}_embeddings.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing embeddings for taxonomy '{name}'. Expected: {path}"
        )
    return load_taxonomy_embeddings(str(path))


# -------------------------------------------------------------
# Main: Map extracted phrases to canonical tags
# -------------------------------------------------------------
def map_phrases_to_canonical(
    extracted_phrases: List[str],
    taxonomy_name: str,
    similarity_threshold: float = 0.51,
) -> List[Dict]:
    """
    Map extracted phrases to canonical tags using semantic similarity.

    Returns a list of dictionaries:
    [
        {
            "tag": canonical_tag,
            "source_text": phrase,
            "confidence": score
        },
        ...
    ]
    """

    # Load embeddings for this taxonomy
    taxonomy_embeddings = load_embeddings(taxonomy_name)
    results = []

    for phrase in extracted_phrases:
        best_tag, score = match_phrase_to_tag(phrase, taxonomy_embeddings)

        # Only keep strong matches
        if score >= similarity_threshold:
            results.append(
                {
                    "tag": best_tag,
                    "source_text": phrase,
                    "confidence": round(score, 4)
                }
            )

    return results


# -------------------------------------------------------------
# Multi-taxonomy wrapper
# -------------------------------------------------------------
def map_all_taxonomies(extracted_phrases: List[str]) -> Dict[str, List[Dict]]:
    """
    Map phrases across all four taxonomy types.
    """

    return {
        "mission_tags": map_phrases_to_canonical(extracted_phrases, "mission_tags"),
        "population_tags": map_phrases_to_canonical(extracted_phrases, "population_tags"),
        "org_type_tags": map_phrases_to_canonical(extracted_phrases, "org_types"),
        "geography_tags": map_phrases_to_canonical(extracted_phrases, "geography_tags"),
        "red_flag_tags": map_phrases_to_canonical(extracted_phrases, "red_flag_tags"),
    }
