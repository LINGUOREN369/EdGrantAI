# Architecture Design

This document describes the high-level architecture of EdGrantAI and how the major components fit together. Detailed workflows and formulas are covered in other docs.

---

## System goals

- Transparent, evidence-bound matching for education nonprofits
- Low maintenance and reproducible outputs
- Clear separation of extraction, mapping, profile building, and matching

---

## High-level flow

1) Ingest raw grant and organization text
2) Extract verbatim keyphrases and deterministic metadata
3) Map phrases to the taxonomy
4) Build structured profiles (grant and organization)
5) Score matches and generate recommendations
6) Write JSON reports

---

## Core modules

- `extraction/`  
  Controlled Keyphrase Extractor and deterministic metadata parsers.

- `mapping/`  
  Canonical mapping (dictionary + embeddings), taxonomy embeddings, and profile builders.

- `matching/`  
  Scoring and recommendation output.

- `common/config.py`  
  Central settings, weights, thresholds, and file paths.

- `prompts/`  
  CKE prompt files (verbatim extraction rules).

---

## Data artifacts

- Taxonomy files: `data/taxonomy/*.json`
- Taxonomy embeddings: `data/taxonomy/embeddings/*_embeddings.json`
- Processed grant profiles: `data/processed_grants/*_profile.json`
- Processed organization profiles: `data/processed_orgs/*_profile.json`
- Recommendation reports: `reports/*_recommendations.json`

---

## Diagrams

- System structure: `docs/structure.png`
- Pipeline flow: `docs/workflow.png`

---

## Where to go next

- Data sources and handling: `docs/00_data_source_and_handling.md`
- Extraction details: `docs/01_extraction.md`
- Profile building: `docs/02_profile_building.md`
- Matching algorithm and formula: `docs/03_matching_algorithm_and_formula.md`
