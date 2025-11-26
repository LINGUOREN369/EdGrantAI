# EdGrantAI — Design Reasoning

This document explains the design principles behind EdGrantAI: the taxonomy, prompt and model choices, embeddings strategy, profile builders, configuration, data storage, matching, thresholds, and operational concerns.

## Purpose & Scope
- Make grant matching transparent, repeatable, and auditable for small education nonprofits.
- Keep the system low‑maintenance and cost‑effective while preserving quality.
- Separate concerns: extractive parsing vs. semantic mapping vs. profile assembly.

## Architecture Overview
- Pipeline stages
  - Extraction (CKE) → Canonical mapping (embeddings) → Profile assembly (JSON)
- Primary modules
  - `pipeline/cke.py`: Controlled Keyphrase Extractor (chat model)
  - `pipeline/embedding_matcher.py`: Embeddings + cosine similarity utilities
  - `pipeline/canonical_mapper.py`: Loads taxonomy embeddings, runs matching/top‑k/thresholds
  - `pipeline/grant_profile_builder.py`: Orchestrates build + CLI
  - `pipeline/build_taxonomy_embeddings.py`: One‑time taxonomy embedding builder
  - `pipeline/config.py`: Central source for paths, models, thresholds, taxonomies
- Data assets
  - Taxonomy JSON: `data/taxonomy/*.json`
  - Taxonomy embeddings: `data/taxonomy/embeddings/*_embeddings.json`
  - Output profiles: `data/processed_grants/{grant_id}_profile.json`
  - Prompt: `prompts/cke_prompt_v1.txt`
- Diagram
  - See `docs/data_flow.md` (Mermaid) and `docs/data_flow.svg` (image).

## Taxonomy Design
- Scope: mission, population, org type, geography, red flags.
- Curation: human‑crafted tags for interpretability, stability, and auditability. Avoids noisy, emergent, or opaque clusters.
- Versioning: `data/taxonomy/schema_version.json` records the taxonomy version; profiles include this version for traceability.
- Change management: when tags change, rebuild taxonomy embeddings for affected taxonomies and consider re‑processing cached profiles.

## Prompt Strategy (CKE)
- Location: `prompts/cke_prompt_v1.txt`.
- Goal: extract only verbatim phrases from the grant text and return a strict JSON array of strings.
- Why a strong prompt?
  - Minimizes hallucinations and paraphrases by constraining output to quotes/verbatim.
  - Produces machine‑parseable JSON that downstream code can rely on.
- Model pairing: `gpt-4o-mini`
  - Reasoning: the task is extractive and tightly constrained; smaller fast models are sufficient, lower cost, and lower latency.
  - Semantic understanding (synonyms, clustering) is deferred to the embedding step.
- Operational notes
  - The code trims common formatting (e.g., code fences) and expects JSON.
  - Consider `temperature=0` and/or structured `response_format` if you decide to wrap the array in an object.

## Models & Rationale
- Chat (extraction): `gpt-4o-mini`
  - Designed for cost‑efficient, constrained extraction with a strong prompt.
- Embeddings (semantic matching): `text-embedding-3-small`
  - Strong quality‑to‑cost ratio for cosine similarity over controlled taxonomy sets.
- Upgrades when needed
  - `text-embedding-3-large` for tighter semantics at higher cost.
  - Strict JSON response formats if you extend schemas.

## Embedding Strategy
- Precompute embeddings for canonical tags per taxonomy and store as JSON.
  - Path: `data/taxonomy/embeddings/*_embeddings.json`
  - Builder: `python -m pipeline.build_taxonomy_embeddings --all`
- Compute embeddings on‑demand for extracted phrases during matching.
- Rationale
  - Precomputation reduces runtime cost and yields stable anchor vectors.
  - On‑demand phrase vectors adapt to input without persisting heavy payloads.

## Grant Profile Building
- Steps
  1) Controlled Keyphrase Extraction (CKE): `pipeline/cke.py`
  2) Canonical mapping via embeddings: `pipeline/canonical_mapper.py`, `pipeline/embedding_matcher.py`
  3) Attach taxonomy version and metadata: `pipeline/grant_profile_builder.py`
  4) Assemble and save JSON profile
- Output contents
  - `grant_id`, `created_at`, `taxonomy_version`
  - `extracted_phrases` (verbatim phrases from CKE)
  - `canonical_tags` (per taxonomy: `{ tag, source_text, confidence }`)
- Exclusions
  - Raw embedding vectors are not stored (size, noise, and version coupling). Profiles stay small and human‑readable.
- CLI
  - Build embeddings once: `python -m pipeline.build_taxonomy_embeddings --all`
  - Build profile: `python -m pipeline.grant_profile_builder data/grants/test_grant_1.txt`

## Organization Profile Building (Concept)
- Mirror the grant pipeline on org text (mission, focus areas, geography) to produce an org profile JSON with canonical tags.
- Store under `data/processed_orgs/{org_id}_profile.json`.
- Optional: enrich with normalized metadata (e.g., org type, IRS status, primary geography).
- Benefit: symmetric, explainable matching between org and grant profiles.

## Matching & Thresholding
- Algorithm
  - For each extracted phrase, embed it and compute cosine similarity with every canonical tag embedding in a taxonomy.
  - Keep up to `TOP_K` tags per phrase that meet or exceed taxonomy threshold.
- Configuration (in `pipeline/config.py`)
  - `TOP_K` (default: 5)
  - Per‑taxonomy thresholds (defaults):
    - mission (0.45), population (0.50), org_type (0.50), geography (0.55), red_flags (0.35), default (0.51)
  - `TAXONOMIES` controls which taxonomies are used (and order)
  - `TAXONOMY_TO_OUTPUT_KEY` maps taxonomy names to profile output keys
- Design principles
  - Geography stricter (false positives are costly); red flags looser (favor recall to catch blockers).
  - `TOP_K > 1` allows phrases to map to multiple relevant tags.
- Calibration guidance
  - Use a small labeled set to adjust thresholds for precision/recall balance per taxonomy.
  - Monitor match counts and distribution; adjust based on domain expert feedback.

## Configuration & Operability
- Centralized settings live in `pipeline/config.py` and are loaded at import.
- Overridable via environment variables (auto‑loaded from `.env`):
  - Chat/Embedding models: `OPENAI_CHAT_MODEL`, `OPENAI_EMBEDDING_MODEL`
  - Matching: `TOP_K`, `THRESHOLD_*`, `TAXONOMIES`
  - Paths: `PROMPTS_DIR`, `CKE_PROMPT_PATH`, `TAXONOMY_DIR`, `TAXONOMY_EMBEDDINGS_DIR`, `SCHEMA_VERSION_PATH`, `PROCESSED_GRANTS_DIR`
- Benefits
  - Tune behavior without code edits, per environment or dataset.

## Precompute vs On‑Demand
- Precomputed (offline)
  - Canonical taxonomy embeddings
  - Optionally: cached profiles for known grants/orgs
- On‑demand (per run)
  - CKE extraction, phrase embeddings, similarity/thresholding
- Optional caches
  - Phrase embedding cache keyed by `(phrase, model)` for speed.

## Data Storage & Database Strategy
- Current: Git‑versioned JSON files (transparent, diff‑friendly, simple)
- Future DB (when scale/queries demand):
  - Tables: `taxonomies`, `taxonomy_tags`, `taxonomy_tag_embeddings`
  - Tables: `grants`, `grant_profiles`, `orgs`, `org_profiles`
  - Tables: `matches` (grant_id, org_id, per‑taxonomy scores, rationale)
  - Keep JSON exports for auditability and portability.

## CLI & Workflows
- Build taxonomy embeddings (once):
  - `python -m pipeline.build_taxonomy_embeddings --all`
- Build a grant profile from a text file:
  - `python -m pipeline.grant_profile_builder data/grants/test_grant_1.txt`
  - With options: `--grant-id`, `--out-dir`

## Performance & Scaling
- Complexity: O(P × T_tax) per taxonomy (P = phrase count, T_tax = tag count)
- Levers
  - Precompute embeddings (done), lower `TOP_K`, raise thresholds, batch embeddings calls, and cache phrase embeddings.
  - Move to ANN/vector DB (e.g., HNSW/FAISS) when taxonomy scales large.

## Testing, Reliability & Monitoring
- Prompt compliance: validate JSON, handle code‑fence wrapping, and set low temperature for determinism.
- Unit tests around parsing/matching; use fixtures with known expected tags.
- Log counts: extracted phrases, matches per taxonomy, filtered candidates.
- Track taxonomy version in profiles for reproducibility.

## Security & Privacy
- Credentials: `OPENAI_API_KEY` via `.env` or environment; never commit secrets.
- Data: profiles exclude embeddings; review storage of original texts per privacy needs.
- Operational limits: consider batching/rate‑limit handling for bulk runs.

## Outputs
- Grant profile JSON: compact, human‑readable, includes evidence (phrases) and canonical tags with confidence.
- Org profile JSON (future): same structure, plus normalized org metadata fields.

## Future Enhancements
- Best‑only toggle: keep single highest‑confidence tag per taxonomy after thresholding.
- Phrase embedding cache to speed repeated runs.
- Add model metadata (chat/embedding model names, thresholds) into profiles for traceability.
- Org profile builder CLI and schema.
- Vector DB integration for larger taxonomies.
- Web UI for nonprofits to paste text and download reports.

## Troubleshooting
- Missing API key: ensure `.env` has `OPENAI_API_KEY` and that it’s loaded; import of `cke.py`/`embedding_matcher.py` requires it.
- Missing embeddings: run `python -m pipeline.build_taxonomy_embeddings --all`.
- Prompt not found: ensure `prompts/cke_prompt_v1.txt` exists.
- JSON parse errors: model output isn’t strict JSON; tighten prompt, set temperature near 0, or use structured response format.

---

_Files referenced match the current repository state._

