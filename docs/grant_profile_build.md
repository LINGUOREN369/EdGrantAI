# How the Grant Profile Is Built

1) Controlled Keyphrase Extraction (CKE)
- Extracts verbatim phrases (1–6 words) using the stored prompt.
- Prompt: `prompts/cke_prompt_nsf_v1.txt`
- Code: `pipeline/cke.py`

2) Canonical Mapping (Dictionary → Embeddings)
- Dictionary pre‑mapping: normalize phrases and map directly to canonical tags/synonyms in `data/taxonomy/synonyms/*` (confidence 1.0).
- Embedding fallback: only if no dictionary match; runs strict thresholds first, then (if needed) a single looser pass for select taxonomies.
- Code: `pipeline/canonical_mapper.py`, `pipeline/embedding_matcher.py`

3) Metadata Attachment
- Reads and attaches the taxonomy version to the profile.
- Code: `pipeline/grant_profile_builder.py:41`

4) Assemble + Save
- Builds and writes `data/processed_grants/{grant_id}_profile.json` with: `grant_id`, `created_at`, `taxonomy_version`, `extracted_phrases`, `canonical_tags`.
- Code: `pipeline/grant_profile_builder.py:52`, `pipeline/grant_profile_builder.py:85`

Timestamps
- `created_at` is recorded in ISO8601 with timezone offset. Default timezone is `America/New_York` and can be overridden via the `TIMEZONE` environment variable.

Source metadata
- The profile also records the provenance of the input under `source`:
  - `source.path`: the local input file path (e.g., `data/grants/test_grant_1.txt`)
  - `source.url`: an optional RFP or website URL (when provided via `--source-url`)

Deadline
- The profile includes a `deadline` block parsed from the text (heuristic):
  - `status` (one of `date`, `multiple`, `rolling`, `unspecified`)
  - `dates` (ISO list when detected — e.g., `2025-03-15`)
  - `raw_mentions` (up to 10 lines with deadline cues)

Notes
- Profiles do not store raw embedding vectors; only phrases and matched tags (with confidence) are saved.
- Synonyms: add manual synonyms in `data/taxonomy/synonyms/<taxonomy>_synonyms.json` and/or auto‑generate format variants via `make synonyms-build`.
- Ensure taxonomy embeddings exist at `data/taxonomy/embeddings/*_embeddings.json` before running mapping.

## CLI

Prerequisites:
- Set `OPENAI_API_KEY` in your `.env` (auto-loaded) or environment.
- Build taxonomy embeddings at least once:
  - `python -m pipeline.build_taxonomy_embeddings --all`

Build a profile from a text file:
- Derive grant id from filename:
  - `python -m pipeline.grant_profile_builder data/grants/text_grant_1.txt`
- Or specify the id and output directory:
  - `python -m pipeline.grant_profile_builder data/grants/text_grant_1.txt --grant-id text_grant_1 --out-dir data/processed_grants`
- Optionally include a source URL:
  - `python -m pipeline.grant_profile_builder data/grants/text_grant_1.txt --source-url https://example.org/rfp`
- Convenience: if the first non-empty line of the `.txt` file is an `http(s)` URL, it is used as `source.url` and removed from the processed text automatically.

Process all `.txt` grants in a directory:
- Use defaults (dir=`data/grants`, ext=`.txt`):
  - `python -m pipeline.grant_profile_builder -all`
- Or customize directory and output location:
  - `python -m pipeline.grant_profile_builder --all --dir data/grants --ext .txt --out-dir data/processed_grants`

Output:
- `data/processed_grants/{grant_id}_profile.json`
- The CLI also prints processing time in seconds.

Canonical tag entries
- Each item in `canonical_tags.<taxonomy>` includes:
  - `tag`: the canonical taxonomy tag
  - `source_text`: the verbatim phrase that matched
  - `confidence`: 1.0 (dictionary) or cosine similarity score (0–1)
