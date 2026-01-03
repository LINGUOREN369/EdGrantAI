# Profile Building

This document covers how grant and organization profiles are built from extracted phrases, including mapping rules, guardrails, and output structure.

---

## Mapping funnel (summary)

1) Dictionary pre-mapping  
   - Exact or synonym match maps at confidence 1.0.
   - Synonyms live in `data/taxonomy/synonyms/`.

2) Guardrails  
   - Prevent common errors (for example: audience terms mapping to organization type).

3) Embedding fallback  
   - Used only when dictionary matching fails.
   - Applies strict thresholds and a single loose fallback for select taxonomies.

4) Selection and dedup  
   - Keep top matches per phrase and deduplicate by canonical tag.
   - Aggregate evidence across phrases.

Mapping code:
- `mapping/canonical_mapper.py`
- `mapping/embedding_matcher.py`

Guardrails enforced during mapping:
- Audience-like phrases cannot create organization type tags.
- Red flags require gating terms and (for grants) eligibility section provenance.
- Mechanism acronyms (for example: REU, CAREER) do not map to mission.
- Computing education tags require explicit computing cues.
- “English learners” requires the word “English”.

Mission selection (grants):
- Only phrases from Introduction or Program Description can become mission.
- A simple scoring favors title matches, Program Description, and repeated phrases.
- Generic mission phrases are demoted to secondary tags.
- See `settings.MISSION_GENERIC_STOPLIST`.

---

## Grant profile output

Built by `mapping/grant_profile_builder.py` and saved to:
- `data/processed_grants/{grant_id}_profile.json`

Core fields:
- `grant_id`
- `created_at`
- `taxonomy_version`
- `extracted_phrases`
- `extracted_phrases_structured` (phrase + section)
- `canonical_tags` (per taxonomy, each with `tag`, `source_text`, `confidence`)
- `source` (path and optional URL)
- `deadline` (parsed metadata)
- `funding` (parsed metadata when present)

---

## Organization profile rules (summary)

Organization profiles use stricter filtering for precision:
- Geography must be explicit (or derived from a named state).
- Grade-band tags are not inferred from a generic "K-12" mention.
- Population tags require explicit wording in the text.
- Red flags require gated language and multiple mentions.
- Organization type must match self-description (avoid audience-driven mislabels).

Org-specific enrichments:
- If “K-12” appears, a broad `K-12 students` tag is added.
- Higher education mentions add `college instructors`.
- State names add a derived `single state` geography tag.
- “Nonprofit” and common edtech phrases add org type tags.

Built by `mapping/org_profile_builder.py` and saved to:
- `data/processed_orgs/{org_id}_profile.json`

---

## Synonyms workflow

- Curated synonyms live in `data/taxonomy/synonyms/`.
- Format-level variants can be generated and merged with:
  - `make synonyms-build`

---

## CLI (common)

- Build taxonomy embeddings once:
  - `python -m mapping.build_taxonomy_embeddings --all`
- Build all grant profiles:
  - `make grants-all`
- Build all organization profiles:
  - `make orgs-all`

---

## Where to go next

- Matching algorithm and formula: `docs/03_matching_algorithm_and_formula.md`
