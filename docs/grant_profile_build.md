# How the Grant Profile Is Built

1) Controlled Keyphrase Extraction
- Extracts verbatim phrases from the grant text via the chat model using your stored prompt.
- Code: `pipeline/cke.py:43`

2) Canonical Mapping (Embeddings)
- Embeds each extracted phrase and compares it against precomputed taxonomy embeddings (cosine similarity). Keeps matches at or above the threshold (default 0.70).
- Code: `pipeline/canonical_mapper.py:60`, `pipeline/canonical_mapper.py:102`, `pipeline/embedding_matcher.py:49`

3) Metadata Attachment
- Reads and attaches the taxonomy version to the profile.
- Code: `pipeline/grant_profile_builder.py:41`

4) Assemble + Save
- Builds and writes `data/processed_grants/{grant_id}_profile.json` with: `grant_id`, `created_at`, `taxonomy_version`, `extracted_phrases`, `canonical_tags`.
- Code: `pipeline/grant_profile_builder.py:52`, `pipeline/grant_profile_builder.py:85`

Source metadata
- The profile also records the provenance of the input under `source`:
  - `source.path`: the local input file path (e.g., `data/grants/test_grant_1.txt`)
  - `source.url`: an optional RFP or website URL (when provided via `--source-url`)

Notes
- Profiles do not store raw embedding vectors; only phrases and matched tags (with confidence) are saved.
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

Output:
- `data/processed_grants/{grant_id}_profile.json`
 - The CLI also prints processing time in seconds.
