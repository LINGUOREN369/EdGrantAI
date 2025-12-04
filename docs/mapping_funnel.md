# Mapping Funnel — Dictionary vs Embeddings

This document explains how extracted phrases flow through the mapping funnel to become canonical tags, how we decide what goes into the dictionary vs. embeddings, and how synonyms are generated, curated, and loaded at runtime.

## Overview

Funnel stages:
1) Normalize + Dictionary pre‑mapping (confidence 1.0)
2) Guardrails (taxonomy‑specific allow/deny)
3) Embedding fallback (strict thresholds → optional loose)
4) Selection + Dedup (Top‑K/Top‑1, aggregate evidence)

Key goals:
- Maximize precision with dictionary hits and guardrails
- Preserve recall via controlled embedding fallback
- Keep outputs auditable with source evidence

## Stage 0 — Extraction (CKE)
- Extract verbatim, short noun phrases from org/grant text.
- Prompt: `prompts/cke_prompt_nsf_v1.txt`
- Code: `pipeline/cke.py`

## Stage 1 — Normalize + Dictionary
- Normalize phrase for lookup (lowercase, strip spaces/punctuation): `pipeline/canonical_mapper.py`
- Load canonical tags + curated synonyms for the taxonomy from `data/taxonomy/synonyms/`.
- If normalized phrase matches a canonical or synonym → map immediately with confidence 1.0, skip embeddings.

Dictionary files (curated)
- Location: `data/taxonomy/synonyms/`
- Per taxonomy: `<taxonomy>_synonyms.json`
- Format: JSON map of `synonym → canonical` (string to string).

Auto variants
- Built by `pipeline/build_synonyms.py` (safe format‑level expansions: acronyms in parens, K–12 forms, Pre‑K, afterschool, districtwide/statewide, higher‑ed shorthand, and/& swap, etc.).
- Command: `make synonyms-build`
- The build merges auto variants into curated files and deletes `*.auto.json` for a clean runtime set (see Makefile).
- Runtime loader ignores `*.auto.json`; it uses only curated files.

What belongs in the dictionary (curated files)
- High‑precision, common variants with clear intent:
  - Acronyms/initialisms (e.g., REU, EHR, EPSCoR, IU/ESC/RESA, LOI)
  - Domain paraphrases (e.g., “informal science education” → “informal STEM learning”)
  - Widely used shorthand (e.g., “LEAs” → “school districts”, “statewide initiative” → “statewide programs”)
- What to avoid:
  - Ambiguous single words or vendor/product names
  - Phrases whose mapping depends heavily on context

## Stage 2 — Guardrails
- Enforced in `pipeline/canonical_mapper.py` to prevent systemic errors:
  - Org types: block audience‑like phrases (e.g., “students”, “teachers”) from mapping to org types.
  - Red flags: require gating terms (only/required/submission limit/LOI/IRB/etc.) in the phrase.
  - Mission computing tags: require explicit computing cues (comput*/CS/coding).
  - Population “English learners”: must include “English” in the phrase to map to “English learners”.

## Stage 3 — Embedding Fallback
- If no dictionary hit, embed the phrase and compare to precomputed canonical tag embeddings.
- Strict thresholds per taxonomy (config in `pipeline/config.py`); if no tags exceed threshold, a single looser pass is tried for select taxonomies (mission/population/org_type). Geography and red flags remain strict by default.
- Embeddings are used for legitimate paraphrases we don’t want to hard‑code.

## Stage 4 — Selection + Dedup
- Top‑K per phrase (or Top‑1 for selected taxonomies via `TOP1_TAXONOMIES`).
- Deduplicate by canonical tag across phrases; keep highest confidence and aggregate `sources` for auditability.

## Curation Workflow
1) Inspect misses: review `extracted_phrases` vs. mappings in processed profiles.
2) Add clear, high‑precision synonyms to curated files under `data/taxonomy/synonyms/`.
3) Build/merge autos: `make synonyms-build` (merges auto → curated, deletes `*.auto.json`).
4) Optionally rebuild embeddings (not required for synonyms): `make rebuild-taxonomy`.
5) Validate: `make validate-taxonomy`.

Guidelines
- Prefer multi‑word, unambiguous phrases; be conservative with single words.
- Use acronyms where a strong expansion exists in your taxonomy.
- Map outreach/OST/partnership phrases where they’re unambiguous (e.g., “LEAs”, “districtwide initiative”).

## Configuration Cheatsheet
- Thresholds: strict/loose values per taxonomy in `pipeline/config.py`.
- Top‑K per taxonomy: `settings.TOP_K_BY_TAXONOMY`.
- Best‑only per taxonomy: `TOP1_TAXONOMIES` env var.
- Synonyms build/merge: `make synonyms-build`.

## Rationale Summary
- Dictionary‑first with guardrails maximizes precision and speed.
- Embeddings recover valid paraphrases without inflating the dictionary.
- Merge‑then‑delete keeps the runtime synonym set single‑sourced and tidy.

