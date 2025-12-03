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
from .embedding_matcher import match_phrase_to_tag, load_taxonomy_embeddings, top_k_matches
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
def _threshold_for_taxonomy(taxonomy_name: str) -> float:
    k = settings.THRESHOLD_KEY_BY_TAXONOMY.get(taxonomy_name, "default")
    return float(settings.THRESHOLDS.get(k, settings.THRESHOLDS.get("default", 0.51)))


def map_phrases_to_canonical(
    extracted_phrases: List[str],
    taxonomy_name: str,
    similarity_threshold: float | None = None,
    top_k: int | None = None,
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

    # Resolve defaults from settings if not provided
    if similarity_threshold is None:
        similarity_threshold = _threshold_for_taxonomy(taxonomy_name)
    if top_k is None:
        top_k = settings.TOP_K_BY_TAXONOMY.get(taxonomy_name, settings.TOP_K)

    top1_gate = taxonomy_name in getattr(settings, "TOP1_TAXONOMIES", [])

    for phrase in extracted_phrases:
        candidates = top_k_matches(phrase, taxonomy_embeddings, k=top_k)
        if top1_gate:
            if candidates:
                tag, score = candidates[0]
                if score >= similarity_threshold:
                    results.append(
                        {
                            "tag": tag,
                            "source_text": phrase,
                            "confidence": round(score, 4),
                        }
                    )
            continue

        for tag, score in candidates:
            if score >= similarity_threshold:
                results.append(
                    {
                        "tag": tag,
                        "source_text": phrase,
                        "confidence": round(score, 4),
                    }
                )

    # Deduplicate by tag across phrases: keep highest confidence; aggregate sources
    best_by_tag: Dict[str, Dict] = {}
    for item in results:
        tag = item["tag"]
        conf = float(item.get("confidence", 0.0))
        if tag not in best_by_tag:
            best_by_tag[tag] = {
                "tag": tag,
                "source_text": item.get("source_text"),
                "confidence": conf,
                "sources": [item.get("source_text")] if item.get("source_text") else [],
            }
        else:
            # Update best confidence and representative source
            if conf > best_by_tag[tag]["confidence"]:
                best_by_tag[tag]["confidence"] = conf
                best_by_tag[tag]["source_text"] = item.get("source_text")
            # Collect all sources
            src = item.get("source_text")
            if src and src not in best_by_tag[tag]["sources"]:
                best_by_tag[tag]["sources"].append(src)

    # Sort by confidence desc for stable output
    deduped = sorted(best_by_tag.values(), key=lambda d: d["confidence"], reverse=True)
    # Re-round confidence for presentation
    for d in deduped:
        d["confidence"] = round(float(d["confidence"]), 4)

    return deduped


# -------------------------------------------------------------
# Multi-taxonomy wrapper
# -------------------------------------------------------------
def map_all_taxonomies(extracted_phrases: List[str]) -> Dict[str, List[Dict]]:
    """
    Map phrases across all four taxonomy types.
    """
    out = {}
    for tax in settings.TAXONOMIES:
        key = settings.TAXONOMY_TO_OUTPUT_KEY.get(tax, tax)
        out[key] = map_phrases_to_canonical(extracted_phrases, tax)
    return out
