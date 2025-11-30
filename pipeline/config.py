"""
Centralized configuration for paths, models and environment.

- Provides a single source of truth for important directories and files.
- Reads values from environment when available; otherwise uses sensible defaults.

Usage:
  from pipeline.config import settings
  print(settings.TAXONOMY_DIR)
"""

from __future__ import annotations

import os
from pathlib import Path

# Ensure .env variables are loaded even when importing submodules directly
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    # If dotenv is not installed, we simply rely on the environment.
    pass


def _repo_root() -> Path:
    # repo root = parent of the package directory
    return Path(__file__).resolve().parents[1]


def _env_path(name: str, default: Path) -> Path:
    val = os.getenv(name)
    return Path(val) if val else default


class Settings:
    def __init__(self) -> None:
        # Filesystem roots
        self.REPO_ROOT: Path = _repo_root()

        # Prompts
        self.PROMPTS_DIR: Path = _env_path("PROMPTS_DIR", self.REPO_ROOT / "prompts")
        self.CKE_PROMPT_PATH: Path = _env_path("CKE_PROMPT_PATH", self.PROMPTS_DIR / "cke_prompt_v1.txt")

        # Taxonomy
        self.TAXONOMY_DIR: Path = _env_path("TAXONOMY_DIR", self.REPO_ROOT / "data" / "taxonomy")
        self.TAXONOMY_EMBEDDINGS_DIR: Path = _env_path("TAXONOMY_EMBEDDINGS_DIR", self.TAXONOMY_DIR / "embeddings")
        self.SCHEMA_VERSION_PATH: Path = _env_path("SCHEMA_VERSION_PATH", self.TAXONOMY_DIR / "schema_version.json")

        # Outputs
        self.PROCESSED_GRANTS_DIR: Path = _env_path("PROCESSED_GRANTS_DIR", self.REPO_ROOT / "data" / "processed_grants")
        self.PROCESSED_ORGS_DIR: Path = _env_path("PROCESSED_ORGS_DIR", self.REPO_ROOT / "data" / "processed_orgs")

        # Models (overridable via env)
        self.OPENAI_CHAT_MODEL: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        self.OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")

        # Matching parameters
        try:
            self.TOP_K: int = int(os.getenv("TOP_K", "5"))
        except ValueError:
            self.TOP_K = 5

        # Per-taxonomy thresholds with a default fallback
        def _f(name: str, default: str) -> float:
            try:
                return float(os.getenv(name, default))
            except ValueError:
                return float(default)

        self.THRESHOLDS = {
            "mission": _f("THRESHOLD_MISSION", "0.50"),        # ↑ from 0.55
            "population": _f("THRESHOLD_POPULATION", "0.60"),  # ↑ big precision
            "org_type": _f("THRESHOLD_ORG_TYPE", "0.50"),      # ↑ slightly
            "geography": _f("THRESHOLD_GEOGRAPHY", "0.55"),    # ↑ strict
            "red_flags": _f("THRESHOLD_RED_FLAGS", "0.70"),    # ↑ very strict
            "default": _f("THRESHOLD_DEFAULT", "0.7"),        # unchanged
        }

        # Taxonomy control — central place to manage which taxonomies are used
        # Comma-separated override supported via TAXONOMIES env var
        _tax = os.getenv("TAXONOMIES")
        if _tax:
            self.TAXONOMIES = [t.strip() for t in _tax.split(",") if t.strip()]
        else:
            self.TAXONOMIES = [
                "mission_tags",
                "population_tags",
                "org_types",
                "geography_tags",
                "red_flag_tags",
            ]

        # Map taxonomy name to threshold key (for THRESHOLDS above)
        self.THRESHOLD_KEY_BY_TAXONOMY = {
            "mission_tags": "mission",
            "population_tags": "population",
            "org_types": "org_type",
            "geography_tags": "geography",
            "red_flag_tags": "red_flags",
        }

        # Output key mapping for map_all_taxonomies results
        # Allows output keys to differ from taxonomy file names
        self.TAXONOMY_TO_OUTPUT_KEY = {
            "mission_tags": "mission_tags",
            "population_tags": "population_tags",
            "org_types": "org_type_tags",
            "geography_tags": "geography_tags",
            "red_flag_tags": "red_flag_tags",
        }

        # Timezone for timestamps (ISO8601 with offset)
        # Override via TIMEZONE (e.g., "America/New_York")
        self.TIMEZONE: str = os.getenv("TIMEZONE", "America/New_York")


# Singleton settings instance
settings = Settings()
