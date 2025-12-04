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

        # Prompts (NSF default; simplified)
        self.PROMPTS_DIR: Path = _env_path("PROMPTS_DIR", self.REPO_ROOT / "prompts")
        self.CKE_PROMPT_PATH: Path = self.PROMPTS_DIR / "cke_prompt_nsf_v1.txt"
        self.MATCHING_EXPLAINER_PROMPT_PATH: Path = _env_path(
            "MATCHING_EXPLAINER_PROMPT_PATH",
            self.PROMPTS_DIR / "matching_explainer_prompt_v1.txt",
        )

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
            "mission": _f("THRESHOLD_MISSION", "0.60"),
            "population": _f("THRESHOLD_POPULATION", "0.65"),
            "org_type": _f("THRESHOLD_ORG_TYPE", "0.75"),
            "geography": _f("THRESHOLD_GEOGRAPHY", "0.85"),
            "red_flags": _f("THRESHOLD_RED_FLAGS", "0.80"),
            "default": _f("THRESHOLD_DEFAULT", "0.70"),
        }

        # Optional looser thresholds used as a fallback when strict pass yields no matches
        self.THRESHOLDS_LOOSE = {
            "mission": _f("THRESHOLD_MISSION_LOOSE", "0.55"),
            "population": _f("THRESHOLD_POPULATION_LOOSE", "0.60"),
            "org_type": _f("THRESHOLD_ORG_TYPE_LOOSE", "0.70"),
            # Keep geography and red_flags strict by default to avoid hallucinations
            "geography": _f("THRESHOLD_GEOGRAPHY_LOOSE", "0.85"),
            "red_flags": _f("THRESHOLD_RED_FLAGS_LOOSE", "0.80"),
            "default": _f("THRESHOLD_DEFAULT_LOOSE", "0.65"),
        }

        # Org profile red-flag requirement: minimal number of explicit mentions in text
        try:
            self.RED_FLAG_MIN_OCCURRENCES_ORG: int = int(os.getenv("RED_FLAG_MIN_OCCURRENCES_ORG", "2"))
        except ValueError:
            self.RED_FLAG_MIN_OCCURRENCES_ORG = 2

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

        # Matching engine (org ↔ grant) parameters
        # Weights sum is not required to be 1.0; they are applied directly
        def _fw(name: str, default: str) -> float:
            try:
                return float(os.getenv(name, default))
            except ValueError:
                return float(default)

        def _fi(name: str, default: str) -> int:
            try:
                return int(os.getenv(name, default))
            except ValueError:
                return int(default)

        self.MATCH_WEIGHTS = {
            # Overlap ratios computed on org-side tag sets
            "mission_tags": _fw("MATCH_W_MISSION", "0.50"),
            "population_tags": _fw("MATCH_W_POPULATION", "0.40"),
            "geography_tags": _fw("MATCH_W_GEOGRAPHY", "0.10"),
            # Org-type treated as eligibility-like (0 or 1)
            "org_type_tags": _fw("MATCH_W_ORG_TYPE", "0.40"),
        }
        # Buckets for Apply/Maybe/Avoid
        self.MATCH_APPLY_THRESHOLD = _fw("MATCH_APPLY_THRESHOLD", "0.60")
        self.MATCH_MAYBE_THRESHOLD = _fw("MATCH_MAYBE_THRESHOLD", "0.40")
        # Penalty multiplier when any red flag present
        self.MATCH_RED_FLAG_PENALTY = _fw("MATCH_RED_FLAG_PENALTY", "0.85")

        # Minimum similarity to count toward taxonomy overlap when using
        # embedding-based similarity between tags
        self.MATCH_TAX_SIM_THRESHOLD = _fw("MATCH_TAX_SIM_THRESHOLD", "0.50")

        # Per‑taxonomy TOP_K (fallback to global TOP_K)
        self.TOP_K_BY_TAXONOMY = {
            "mission_tags": _fi("TOP_K_MISSION", "8"),
            "population_tags": _fi("TOP_K_POPULATION", "7"),
            "org_types": _fi("TOP_K_ORG_TYPE", "5"),
            "geography_tags": _fi("TOP_K_GEOGRAPHY", "5"),
            "red_flag_tags": _fi("TOP_K_RED_FLAGS", "5"),
        }

        # Taxonomies for which we keep at most the top‑1 match per phrase
        _top1 = os.getenv("TOP1_TAXONOMIES")
        if _top1:
            self.TOP1_TAXONOMIES = [t.strip() for t in _top1.split(",") if t.strip()]
        else:
            self.TOP1_TAXONOMIES = []

        # Red-flag hard blocks: if present in grant and org_type_tags do not meet
        # the required one-of set, the match is hard-blocked to Avoid
        self.MATCH_HARD_BLOCKS = {
            "higher_education_only": {
                "org_type_tags": {
                    "any_of": [
                        "higher_education_institution",
                        "four_year_university",
                        "community_college",
                    ]
                }
            },
            "universities_only": {
                "org_type_tags": {
                    "any_of": [
                        "higher_education_institution",
                        "four_year_university",
                        "community_college",
                    ]
                }
            },
            "schools_only": {
                "org_type_tags": {
                    "any_of": [
                        "public_school_district",
                        "public_school_single_site",
                        "charter_school_single_site",
                        "charter_school_network",
                        "independent_private_school",
                    ]
                }
            },
            "government_entities_only": {
                "org_type_tags": {
                    "any_of": [
                        "government_agency_local",
                        "government_agency_state",
                        "education_service_agency",
                    ]
                }
            },
            "nonprofits_only": {
                "org_type_tags": {"any_of": ["nonprofit_501c3", "community_based_organization"]}
            },
        }


# Singleton settings instance
settings = Settings()
