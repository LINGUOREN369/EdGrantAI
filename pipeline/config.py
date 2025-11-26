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

        # Models (overridable via env)
        self.OPENAI_CHAT_MODEL: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        self.OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


# Singleton settings instance
settings = Settings()
