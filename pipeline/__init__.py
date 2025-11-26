"""
Pipeline package entrypoints.

Exposes high-level functions for:
  - run_cke: Controlled Keyphrase Extractor
  - map_all_taxonomies: Canonical tag mapper
  - build_grant_profile / process_grant: Grant profile builder

Usage examples:
  - from pipeline import run_cke, map_all_taxonomies, process_grant
    phrases = run_cke("text")
    tags = map_all_taxonomies(phrases)
    out = process_grant("grant_0001", "text")
"""

from .cke import run_cke
from .canonical_mapper import map_all_taxonomies
from .grant_profile_builder import build_grant_profile, process_grant

__all__ = [
    "run_cke",
    "map_all_taxonomies",
    "build_grant_profile",
    "process_grant",
]
