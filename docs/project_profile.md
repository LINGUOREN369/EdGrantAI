# EdGrantAI — Project Profile

- Name: EdGrant AI
- One-liner: Transparent grant matching for small education nonprofits
- Repo: https://github.com/LINGUOREN369/EdGrantAI

## Overview
EdGrant AI helps small education nonprofits quickly understand which grants fit their mission, which they are eligible for, which to avoid, and why — using structured, explainable matching rather than ad‑hoc lists.

## Key Features
- Structured, explainable matching with evidence
- Education-specific taxonomy and guardrails
- Curated evergreen education grants (NSF-first)
- Eligibility and geography checks with red-flag warnings
- Clear Grant Fit Reports (Apply / Maybe / Avoid)

## Why NSF (Initial Focus)
NSF distributes billions annually but competition is rising and agencies cannot recommend or rank programs for applicants. EdGrant AI fills this gap with transparent, legally permissible matching for nonprofits, RPPs, and education orgs.

## Architecture
- Extract keyphrases (verbatim) from real RFP text
- Map phrases to canonical taxonomy (dictionary → embeddings)
- Build one JSON profile per grant and per org
- Rank matches with transparent scoring + optional explanations

See: `docs/structure.png`, `docs/workflow.png`

## Repository Structure (Highlights)
- Data: `data/grants`, `data/processed_grants`, `data/processed_orgs`, `data/taxonomy`
- Pipeline: `pipeline/*.py` (profile builders, mapper, matcher)
- Prompts: `prompts/*.txt`
- Docs: `docs/*.md`

## Setup
- Python 3.10 recommended
- `pip install -r requirements.txt`
- Add `.env` with `OPENAI_API_KEY=...`

## Quickstart
1) Rebuild taxonomy embeddings: `make rebuild-taxonomy`
2) Process inputs into profiles:
   - Grants: `make grants-all`
   - Orgs: `make orgs-all`
3) Generate recommendations:
   - One org: `make recs ORG=data/processed_orgs/<org>_profile.json TOP=10`

Examples:
- Org profile: `data/processed_orgs/khan_profile.json`
- Grant profile: `data/processed_grants/nsf_REU_profile.json`
- Ranked recs: `reports/khan_recommendations.json`

## Links
- README: `README.md`
- Pipeline details: `docs/grant_profile_build.md`
- Org profile rules: `docs/org_profile_rules.md`
- Mapping funnel: `docs/mapping_funnel.md`

