"""
Grant profile builder.

Runs the end-to-end pipeline:
  1) Controlled Keyphrase Extraction (CKE)
  2) Canonical mapping across taxonomies
  3) Attach taxonomy version and metadata
  4) Save profile (optional)

Usage examples:
  - from pipeline.grant_profile_builder import process_grant
    path = process_grant("grant_0001", "Grant text here.")

Outputs:
  - JSON file saved to data/processed_grants/<grant_id>_profile.json

Environment:
  Requires OPENAI_API_KEY and taxonomy assets in data/taxonomy/.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from .cke import run_cke
from .canonical_mapper import map_all_taxonomies
from .config import settings

# Save location for processed grant profiles
OUTPUT_DIR = settings.PROCESSED_GRANTS_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Path to taxonomy schema version
SCHEMA_VERSION_PATH = settings.SCHEMA_VERSION_PATH


# -------------------------------------------------------------
# Helper: Load taxonomy version
# -------------------------------------------------------------
def load_taxonomy_version() -> str:
    if SCHEMA_VERSION_PATH.exists():
        with open(SCHEMA_VERSION_PATH, "r") as f:
            data = json.load(f)
            return data.get("taxonomy_version", "0.0.0")
    return "0.0.0"


# -------------------------------------------------------------
# Main: Build a full structured grant profile
# -------------------------------------------------------------
def build_grant_profile(grant_id: str, grant_text: str) -> Dict:
    """
    Full pipeline:
    1. Extract keyphrases via CKE
    2. Map phrases to canonical tags
    3. Attach taxonomy version & metadata
    4. Produce final grant profile
    """

    # Step 1 — Controlled Keyphrase Extraction
    extracted_phrases = run_cke(grant_text)

    # Step 2 — Canonical Mapping
    mapped_tags = map_all_taxonomies(extracted_phrases)

    # Step 3 — Load taxonomy version
    version = load_taxonomy_version()

    # Step 4 — Construct final profile
    profile = {
        "grant_id": grant_id,
        "created_at": datetime.utcnow().isoformat(),
        "taxonomy_version": version,
        "extracted_phrases": extracted_phrases,
        "canonical_tags": mapped_tags,
    }

    return profile


# -------------------------------------------------------------
# Save profile to disk
# -------------------------------------------------------------
def save_grant_profile(profile: Dict) -> Path:
    grant_id = profile.get("grant_id", "unknown_grant")
    output_path = OUTPUT_DIR / f"{grant_id}_profile.json"

    with open(output_path, "w") as f:
        json.dump(profile, f, indent=2)

    return output_path


# -------------------------------------------------------------
# Convenience wrapper: run + save
# -------------------------------------------------------------
def process_grant(grant_id: str, grant_text: str) -> Path:
    profile = build_grant_profile(grant_id, grant_text)
    return save_grant_profile(profile)


# Example usage (commented for safety)
# if __name__ == "__main__":
#     text = "We support robotics clubs and maker labs for middle school girls."
#     path = process_grant("grant_0001", text)
#     print(f"Profile saved to: {path}")
