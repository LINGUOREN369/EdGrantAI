# Makefile Commands

This document lists the most common Makefile targets and what they do.

---

## Taxonomy and embeddings

- `make rebuild-taxonomy`  
  Rebuild embeddings for all taxonomies (force).

- `make validate-taxonomy`  
  Validate taxonomy lists vs embeddings (strict).

- `make taxonomy-refresh`  
  Rebuild then validate (one-shot).

- `make synonyms-build`  
  Generate safe synonym variants and merge into curated synonym files.

---

## Grant and organization processing

- `make grants-all`  
  Process all grant text files in `data/grants` into `data/processed_grants`.

- `make orgs-all`  
  Process all organization text files in `data/orgs` into `data/processed_orgs`.

- `make grants-batch`  
  Process the next N grant profiles (default `COUNT=20`).

---

## Recommendations

- `make recs ORG=data/processed_orgs/<org>_profile.json [TOP=10]`  
  Generate recommendations for one organization and write to `reports/`.

- `make recs-all`  
  Generate recommendations for all organization profiles and write to `reports/`.

---

## Source refresh

- `make grants-refresh`  
  Rebuild grant text files from the maintained CSV and filter to core sections.

- `make nsf-from-csv`  
  Build grant text files from a CSV (with optional URL fetching).

- `make nsf-download`  
  Download NSF opportunities (Grants.gov).

- `make nsf-awards-download`  
  Download NSF awards.

- `make nsf-opps-download`  
  Scrape NSF funding opportunity pages.

---

## End-to-end

- `make e2e`  
  Full run: taxonomy refresh, grants refresh, batch build, orgs, and recommendations.

---

## Notes

- Set `OPENAI_API_KEY` in `.env` for extraction and embeddings.
- Most targets accept environment overrides (see `Makefile` for details).
