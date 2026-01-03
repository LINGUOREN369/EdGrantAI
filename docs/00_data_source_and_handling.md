# Data Source and Handling

This document covers where data comes from, how it is stored, and how source text is filtered before extraction and profiling.

---

## Primary source

Grants:
- Curated CSV input (`make nsf-from-csv` or `make grants-refresh`)

Organizations:
- Organization text files in `data/orgs/`

---

## Raw storage layout

- Raw grants: `data/grants/*.txt`
- Raw organizations: `data/orgs/*.txt`
- Processed profiles: `data/processed_grants/` and `data/processed_orgs/`

If the first non-empty line of a grant text file is an `http(s)` URL, it is captured as `source.url` and removed from the text before processing.

---

## Section filtering (grant text)

When building grant text from CSV or scraping:
- Only program-relevant sections are retained (for example: Introduction, Program Description, Award Information, Eligibility Information).
- Items missing required sections can be skipped during refresh.
- This reduces noise and improves extraction precision.

See `extraction/build_grants_from_csv.py` and `extraction/refresh_grants.py` for the exact rules.

---

## Provenance and traceability

Processed profiles retain source metadata:
- `source.path`: local file path
- `source.url`: source URL (if known)

This ensures recommendations are traceable to the original text.

---

## Refresh workflow (typical)

1) Update raw grant text
   - `make grants-refresh` or `make nsf-from-csv`
2) Rebuild grant profiles
   - `make grants-all`
3) Rebuild org profiles (if org inputs changed)
   - `make orgs-all`
4) Re-run recommendations
   - `make recs-all`

---

## CSV path

Set the CSV path when running:

- `CSV=path/to/file.csv make grants-refresh`
- `CSV=path/to/file.csv make nsf-from-csv`

---

## Where to go next

- Extraction details: `docs/01_extraction.md`
- Profile building: `docs/02_profile_building.md`
