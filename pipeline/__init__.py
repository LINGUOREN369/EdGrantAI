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

Note:
  Submodules are imported lazily to avoid side effects during package import
  (e.g., running CLI modules with `python -m pipeline.<module>` without warnings).
"""

__all__ = [
    "run_cke",
    "map_all_taxonomies",
    "build_grant_profile",
    "process_grant",
]


def __getattr__(name):  # PEP 562: lazy attribute access
    if name == "run_cke":
        from .cke import run_cke as _run_cke
        return _run_cke
    if name == "map_all_taxonomies":
        from .canonical_mapper import map_all_taxonomies as _map_all
        return _map_all
    if name in ("build_grant_profile", "process_grant"):
        from .grant_profile_builder import build_grant_profile as _b, process_grant as _p
        return {"build_grant_profile": _b, "process_grant": _p}[name]
    raise AttributeError(f"module 'pipeline' has no attribute {name!r}")
