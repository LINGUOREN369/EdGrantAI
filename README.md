# EdGrant AI

A lightweight, transparent, and high-impact grant-matching system for small education nonprofits.

---

## Overview

EdGrant AI helps small education nonprofits quickly understand:
- Which grants fit their mission
- Which grants they are actually eligible for
- Which grants they should not waste time applying to
- Why a grant is or is not a good match

Instead of giving nonprofits a random list of grants (like ChatGPT would), EdGrant AI provides:
- Structured, explainable matching
- Taxonomy-driven tagging
- Curated evergreen education grants
- Eligibility analysis and red flags
- Clear Grant Fit Reports

EdGrant AI exists because **education funding is becoming less stable, more competitive, and increasingly dominated by private actors**. As public dollars decline, education nonprofits must rely on foundations, CSR programs, and individual philanthropists, but these opportunities are scattered across PDFs, poorly indexed, filled with jargon, and time-consuming to interpret. Large organizations have development teams to manage this complexity. **Small education nonprofits do not.** My mission is to bring structure, transparency, and equity to this landscape—and to ensure that smaller organizations are not left behind.

EdGrant AI is built to be low-maintenance and high-impact — ideal for small education nonprofits with limited staff and no full-time grant writers.

Note on scope: EdGrantAI is currently NSF-first. The initial database and workflows focus on NSF solicitations and education programs, with a design that can expand to additional funders later.

---

## NSF-Only: Competition + Federal Constraints

### Why NSF — and Why Now

Despite recent budget pressure and reductions in certain programs, NSF still distributes billions of dollars every year, including a sizable portfolio of education, STEM, and workforce grants. The money is still there — but competition is increasing sharply.

Competition is getting worse
- Success rates for many NSF education programs are falling
- More institutions are chasing fewer awards
- Small nonprofits, community colleges, and RPPs often lack grant officers
- Even universities struggle to monitor shifting solicitations
- Proposal misalignment is now one of the top reasons for early rejection

This means the cost of applying to the wrong solicitation is higher than ever. Teams routinely waste 40–80 hours on a proposal that was doomed from the start because:
- eligibility wasn’t met
- a required partner wasn’t established
- the program was meant for universities only
- the project did not match the directorate’s scope

EdGrant AI eliminates this waste by showing nonprofits exactly which NSF programs fit — and which do not.

---

### Federal vs. Private Grants

Federal programs like NSF operate under open competition: organizations must apply without prior invitation. Success rates for many programs often hover around 10–20%, and proposals are time‑intensive to prepare. This makes choosing the right opportunity critical.

- Federal (NSF): Open competition; applicants must apply first; many programs have ~10–20% success rates; applications are detailed and time‑consuming; agencies must remain neutral and cannot pre‑screen or recommend programs; despite budget pressures, overall funding remains large while competition rises.
- Private (e.g., Gates Foundation): Frequently invite‑only or curated RFPs; unsolicited applications are rarely accepted; funders pre‑select organizations they view as strong fits; fewer truly open opportunities; less time wasted applying if you are not invited.

Because private cycles are often invitation‑only, the greatest ROI for a transparent matching tool is in the federal space, where anyone can apply — but applicants must choose wisely. EdGrant AI is designed to help small nonprofits invest time only where they are genuinely competitive.

---

### Why NSF Can’t Solve This Problem

A critical and often misunderstood fact: Federal agencies are legally prohibited from recommending or ranking grants for applicants.

They cannot:
- Suggest which program you should apply to
- Tell you which program “fits” your organization
- Provide personalized matching
- Pre-screen your eligibility
- Rank solicitations or give strategic advice

Doing so would violate federal procurement rules, fairness requirements, and open competition mandates.

This means:
- NSF cannot build a matching system
- Universities build their own internal systems, but they are private
- Small nonprofits are left with nothing

EdGrant AI fills this gap by providing public, transparent, and legally permissible grant intelligence that NSF itself cannot provide.

---

### How EdGrant AI Helps in a High-Competition, High-Uncertainty NSF Landscape

EdGrant AI provides:
- Automatically updated NSF solicitations
- Eligibility analysis (who can actually apply?)
- Required partner detection
- Mission and scope alignment scoring
- Red-flag warnings for structural blockers
- Clear “Apply / Maybe / Avoid” recommendations

In a competitive environment, this system:
- Keeps small nonprofits from wasting hundreds of hours
- Helps teams target only viable NSF programs
- Removes guesswork about eligibility
- Helps RPPs and education organizations apply strategically
- Levels a playing field that increasingly favors large institutions

The funding is still there — but only for organizations who apply intelligently. EdGrant AI helps them do exactly that.

---

## Why Not Just Use ChatGPT?

![edgrantai](docs/workflow.png)

Nonprofits can ask ChatGPT for a list of grants. But ChatGPT often produces:
- One-off suggestions
- Hallucinated (graduate students == homeless) or invalid grants
- Expired deadlines
- No eligibility validation
- No mission alignment scoring
- No transparency in reasoning

EdGrant AI is fundamentally different:
- Uses a curated, education-specific taxonomy
- Extracts structured JSON from real RFPs
- Evaluates mission alignment with explainability
- Checks eligibility and geography requirements
- Flags "red-flag" blockers (e.g., district partner required)
- Produces transparent, repeatable Grant Fit Reports

---

## System Architecture

![System Architecture](docs/workflow.png)

- One JSON profile per grant
- One JSON profile per nonprofit
- Matching is transparent and explainable

---


## Repository Structure

```
EdGrantAI/
│
├── README.md
├── LICENSE
├── requirements.txt
├── environment.yml
├── Makefile
│
├── data/
│   ├── grants/
│   ├── orgs/
│   ├── processed_grants/
│   ├── processed_orgs/
│   └── taxonomy/
│       ├── mission_tags.json
│       ├── population_tags.json
│       ├── org_types.json
│       ├── geography_tags.json
│       ├── red_flag_tags.json
│       ├── schema_version.json
│       ├── changelog.md
│       ├── synonyms/
│       │   ├── mission_tags_synonyms.json
│       │   ├── population_tags_synonyms.json
│       │   ├── org_types_synonyms.json
│       │   ├── geography_tags_synonyms.json
│       │   ├── red_flag_tags_synonyms.json
│       │   └── nsf_programs_synonyms.json
│       └── embeddings/
│           ├── mission_tags_embeddings.json
│           ├── population_tags_embeddings.json
│           ├── org_types_embeddings.json
│           ├── geography_tags_embeddings.json
│           └── red_flag_tags_embeddings.json
│
├── docs/
│   ├── architecture.png
│   ├── workflow.png
│   ├── v0.0.1workflow.png
│   ├── Tagging Pipeline Overview.md
│   ├── design_reasoning.md
│   ├── grant_profile_build.md
│   └── org_profile_rules.md
│
├── pipeline/
│   ├── __init__.py
│   ├── config.py
│   ├── cke.py
│   ├── canonical_mapper.py
│   ├── embedding_matcher.py
│   ├── grant_profile_builder.py
│   ├── org_profile_builder.py
│   ├── build_taxonomy_embeddings.py
│   ├── validate_taxonomy.py
│   ├── build_synonyms.py
│   ├── merge_auto_synonyms.py
│   ├── deadline_extractor.py
│   └── matching_engine.py
│
└── prompts/
    ├── cke_prompt_nsf_v1.txt
    └── matching_explainer_prompt_v1.txt
```

---

## Setup

- Python: 3.10 recommended (see `environment.yml` if you prefer Conda).
- Install dependencies (for GitHub dependency graph and runtime):
  - `pip install -r requirements.txt`
- Create a `.env` file in the repo root with your OpenAI API key:
  - `OPENAI_API_KEY=sk-...`

Note: The OpenAI client is initialized at import in `pipeline/cke.py` and `pipeline/embedding_matcher.py`. Ensure your `.env` (or environment) provides `OPENAI_API_KEY` before importing these modules.

---

## Configuration

Centralized configuration lives in `pipeline/config.py` and auto-loads `.env` variables on import.

- Key paths (override via environment if desired):
  - `PROMPTS_DIR` (default: `prompts/`)
  - CKE prompt: fixed to `prompts/cke_prompt_nsf_v1.txt`
  - `MATCHING_EXPLAINER_PROMPT_PATH` (default: `prompts/matching_explainer_prompt_v1.txt`)
  - `TAXONOMY_DIR` (default: `data/taxonomy/`)
  - `TAXONOMY_EMBEDDINGS_DIR` (default: `data/taxonomy/embeddings/`)
  - `SCHEMA_VERSION_PATH` (default: `data/taxonomy/schema_version.json`)
  - `PROCESSED_GRANTS_DIR` (default: `data/processed_grants/`)
  - `PROCESSED_ORGS_DIR` (default: `data/processed_orgs/`)
- Model names (override via env):
  - `OPENAI_CHAT_MODEL` (default: `gpt-4o-mini`)
  - `OPENAI_EMBEDDING_MODEL` (default: `text-embedding-3-large`)
  - `TOP_K` (default: `5`)
  - Per‑taxonomy K (overrides `TOP_K`):
    - `TOP_K_MISSION` (default: `8`)
    - `TOP_K_POPULATION` (default: `7`)
    - `TOP_K_ORG_TYPE` (default: `5`)
    - `TOP_K_GEOGRAPHY` (default: `5`)
    - `TOP_K_RED_FLAGS` (default: `5`)
  - `THRESHOLD_MISSION` (default: `0.60`)
  - `THRESHOLD_POPULATION` (default: `0.65`)
  - `THRESHOLD_ORG_TYPE` (default: `0.75`)
  - `THRESHOLD_GEOGRAPHY` (default: `0.85`)
  - `THRESHOLD_RED_FLAGS` (default: `0.80`)
  - `THRESHOLD_DEFAULT` (default: `0.70`)
  - `TIMEZONE` (default: `America/New_York` for `created_at` timestamps)
  - `TOP1_TAXONOMIES` (comma‑sep; default: empty) — only the best tag per phrase is kept for listed taxonomies.
  - `RED_FLAG_MIN_OCCURRENCES_ORG` (default: `2`) — org profiles keep a red flag only if its triggering phrase(s) appear at least this many times in the org text.

Two‑stage thresholds (strict → loose)
- The mapper attempts dictionary matches first (confidence 1.0). If none, it runs embeddings with strict thresholds, then optionally retries with looser thresholds if nothing matched.
- Defaults (strict):
  - `THRESHOLD_MISSION`=0.60, `THRESHOLD_POPULATION`=0.65, `THRESHOLD_ORG_TYPE`=0.75, `THRESHOLD_GEOGRAPHY`=0.85, `THRESHOLD_RED_FLAGS`=0.80
- Defaults (loose, only used if strict yields no matches):
  - `THRESHOLD_MISSION_LOOSE`=0.55, `THRESHOLD_POPULATION_LOOSE`=0.60, `THRESHOLD_ORG_TYPE_LOOSE`=0.70
  - `THRESHOLD_GEOGRAPHY_LOOSE`=0.85, `THRESHOLD_RED_FLAGS_LOOSE`=0.80 (kept strict by default)

NSF-specific prompt
- The Controlled Keyphrase Extractor uses the NSF‑focused prompt at `prompts/cke_prompt_nsf_v1.txt`.
- No configuration is required.

---

## Makefile Shortcuts

Use the provided Make targets to keep taxonomies in sync:

- Rebuild embeddings for all taxonomies (force):
  - `make rebuild-taxonomy`
- Validate taxonomy lists vs. embeddings (strict):
  - `make validate-taxonomy`
- Rebuild then validate in one go:
  - `make taxonomy-refresh`

- Generate synonyms (safe, format-level variants) for all taxonomies:
  - `make synonyms-build`

Quick embeddings rebuild checklist
- Rebuild taxonomy embeddings:
  - `make rebuild-taxonomy`
- Validate embeddings vs. taxonomy lists:
  - `make validate-taxonomy`

- Process all profiles from text files:
  - Grants: `make grants-all` (reads from `data/grants`, writes to `data/processed_grants`)
  - Orgs: `make orgs-all` (reads from `data/orgs`, writes to `data/processed_orgs`)

- Matching engine (rank grants for org profiles):
  - One org: `make recs ORG=data/processed_orgs/<org>_profile.json [TOP=10] [GRANTS_DIR=data/processed_grants] [OUT=reports/<org>_recommendations.json]`
  - All orgs: `make recs-all` (reads from `data/processed_orgs`, writes JSON files to `reports/`)

Notes
- `make recs` includes an LLM-generated explanation per grant with a one-line recommendation and up to 5 bullets under `explanation` in the JSON output.

These commands assume `.env` contains `OPENAI_API_KEY` (auto‑loaded by the pipeline).

---

## Data Design

Grant profile JSON structure (produced by the pipeline):

```json
{
  "grant_id": "nsf_AISL",
  "created_at": "2025-01-02T12:34:56-05:00",
  "taxonomy_version": "0.0.10",
  "extracted_phrases": ["informal STEM learning", "letters of collaboration", "United States"],
  "canonical_tags": {
    "mission_tags": [{"tag": "informal STEM learning", "source_text": "informal STEM learning", "confidence": 1.0}],
    "population_tags": [],
    "org_type_tags": [],
    "geography_tags": [{"tag": "United States", "source_text": "United States", "confidence": 1.0}],
    "red_flag_tags": [{"tag": "letters of collaboration", "source_text": "letters of collaboration", "confidence": 1.0}]
  },
  "deadline": {"status": "date", "dates": ["2025-01-08"], "raw_mentions": ["Full proposals due January 8, 2025"]},
  "source": {"path": "data/grants/nsf_AISL.txt", "url": "https://www.nsf.gov/..."}
}
```

Notes
- Profiles store evidence (verbatim phrases) and canonical tags with confidence; no raw vector data.
- A `funding` block is optional; if present, the matching engine will include `estimated_min`/`estimated_max` in reports.

---

## Taxonomy (Education-Focused)

EdGrant AI uses a hand-curated education taxonomy (not clustering). This ensures consistent and meaningful matching.

**Mission Tags**

Examples: literacy, STEM, learning recovery, teacher PD, education equity, EdTech, college access.

**Population Tags**

Examples: low-income, ELL, students with disabilities, BIPOC students, rural students, K–3, high school.

**Org Type Tags**

Examples: nonprofit, school district, university, community-based organization.

**Geography Tags**

Examples: US National, state-specific, New England, global.

**Red Flag Tags**

Examples: "Requires district partner," "Invitation-only," "Only funds universities."

---

## Synonyms (Dictionary Pre‑Mapping)

Before embedding similarity, extracted phrases are first matched via a case/space/punctuation‑insensitive dictionary against canonical tags and curated synonym files:

- Location: `data/taxonomy/synonyms/`
- Files (curated, per taxonomy):
  - `mission_tags_synonyms.json`
  - `population_tags_synonyms.json`
  - `org_types_synonyms.json`
  - `geography_tags_synonyms.json`
  - `red_flag_tags_synonyms.json`
  - `nsf_programs_synonyms.json`

Format: JSON object mapping synonym phrase → canonical tag (string to string). Example:

```
{
  "teacher pd": "teacher professional development",
  "ai tutoring": "AI-powered tutoring",
  "oer": "open educational resources (OER)"
}
```

Build/merge workflow:
- Generate safe format‑level variants and merge into curated files: `make synonyms-build`
  - Auto variants: `pipeline/build_synonyms.py` creates `<taxonomy>_synonyms.auto.json` (e.g., paren acronyms, K–12 forms, afterschool/Pre‑K, districtwide, higher‑ed shorthand).
  - Merge step: `pipeline/merge_auto_synonyms.py` folds autos into curated files and deletes `*.auto.json` to keep runtime tidy.
  - Runtime uses curated files only; autos are ignored by the loader.

Behavior:
- Dictionary matches (with normalization) map at confidence 1.0 and skip embeddings.
- If no dictionary match, the system falls back to embedding similarity with thresholds (strict → optional loose).
- Guardrails still apply (e.g., audience terms cannot map to org_type; red flags require gating terms; explicit computing/English cues).

When to add to dictionary vs. rely on embeddings:
- Add to dictionary: common, high‑precision acronyms and paraphrases (REU, EHR, EPSCoR, LEAs; “informal science education”).
- Use embeddings: ambiguous single‑word terms, vendor names, or phrases whose mapping is highly context‑dependent.

See also: `docs/mapping_funnel.md` for the full funnel and curation policy.

---

## Matching Engine

A transparent scoring system based on:

Mission Alignment     50%
Eligibility Fit       40%
Geography Fit         10%

Outputs include:
- Ranked list of grants
- Matching rationale
- Eligibility issues
- Red-flag warnings
- Funding ranges and deadlines

---

## Grant Fit Report

Each nonprofit receives:
- Top aligned grants
- Why they match
- Red flags
- Eligibility summary
- Priority ranking (apply / maybe / avoid)

This helps nonprofits avoid wasting 30–50 hours on ineligible grants.

---

## Quickstart

1) Install and set env
- `pip install -r requirements.txt`
- Create `.env` with `OPENAI_API_KEY=...`

2) Build taxonomy embeddings (once)
- `make rebuild-taxonomy`

3) Process inputs into profiles
- Grants from text files: `make grants-all` (reads `data/grants/*.txt` → writes `data/processed_grants/*_profile.json`)
- Orgs from text files: `make orgs-all` (reads `data/orgs/*.txt` → writes `data/processed_orgs/*_profile.json`)

4) Generate recommendations
- One org: `make recs ORG=data/processed_orgs/<org>_profile.json [TOP=10]`
- All orgs: `make recs-all` (writes JSON files under `reports/`)

---

## Programmatic Usage

- Extract keyphrases via CKE:
  - `from pipeline.cke import run_cke`
  - `phrases = run_cke("We support robotics clubs...")`
- Map phrases to canonical taxonomy:
  - `from pipeline.canonical_mapper import map_all_taxonomies`
  - `mapped = map_all_taxonomies(phrases)`
- Build and save a full grant profile:
  - `from pipeline.grant_profile_builder import process_grant`
  - `path = process_grant("grant_0001", "grant description text...")`

---

## How the Grant Profile Is Built

See `docs/grant_profile_build.md` for the detailed steps.

Org profiles apply additional rules for higher precision (dictionary‑first, strict geography, mission/grade‑band/policy checks, population constraints, and per‑taxonomy thresholds). See:
- `docs/org_profile_rules.md`
- `docs/mapping_funnel.md` (dictionary → guardrails → embeddings)

---

## Future Roadmap

- Lightweight FastAPI backend
- Website for nonprofits to paste mission statements
- Auto-ingest RFP URLs for structured extraction
- "Grant alerts" based on mission alignment
- Multi-tenant nonprofit profile storage

---

## Mission

EdGrant AI’s mission is to support small education nonprofits that often lack staff, capacity, and grant-writing resources. By providing transparent, trustworthy funding intelligence, EdGrant AI helps democratize access to education funding.
