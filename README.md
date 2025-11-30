# EduGrant AI

A lightweight, transparent, and high-impact grant-matching system for small education nonprofits.

---

## Overview

EduGrant AI helps small education nonprofits quickly understand:
- Which grants fit their mission
- Which grants they are actually eligible for
- Which grants they should not waste time applying to
- Why a grant is or is not a good match

Instead of giving nonprofits a random list of grants (like ChatGPT would), EduGrant AI provides:
- Structured, explainable matching
- Taxonomy-driven tagging
- Curated evergreen education grants
- Eligibility analysis and red flags
- Clear Grant Fit Reports

EduGrant AI exists because **education funding is becoming less stable, more competitive, and increasingly dominated by private actors**. As public dollars decline, education nonprofits must rely on foundations, CSR programs, and individual philanthropists, but these opportunities are scattered across PDFs, poorly indexed, filled with jargon, and time-consuming to interpret. Large organizations have development teams to manage this complexity. **Small education nonprofits do not.** My mission is to bring structure, transparency, and equity to this landscape—and to ensure that smaller organizations are not left behind.

EduGrant AI is built to be low-maintenance and high-impact — ideal for small education nonprofits with limited staff and no full-time grant writers.

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

EduGrant AI eliminates this waste by showing nonprofits exactly which NSF programs fit — and which do not.

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

EduGrant AI fills this gap by providing public, transparent, and legally permissible grant intelligence that NSF itself cannot provide.

---

### How EduGrant AI Helps in a High-Competition, High-Uncertainty NSF Landscape

EduGrant AI provides:
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

The funding is still there — but only for organizations who apply intelligently. EduGrant AI helps them do exactly that.

---

## Why Not Just Use ChatGPT?

![edgrantai](docs/workflow.png)

Nonprofits can ask ChatGPT for a list of grants. But ChatGPT often produces:
- One-off suggestions
- Hallucinated or invalid grants
- Expired deadlines
- No eligibility validation
- No mission alignment scoring
- No transparency in reasoning

EduGrant AI is fundamentally different:
- Uses a curated, education-specific taxonomy
- Extracts structured JSON from real RFPs
- Evaluates mission alignment with explainability
- Checks eligibility and geography requirements
- Flags "red-flag" blockers (e.g., district partner required)
- Produces transparent, repeatable Grant Fit Reports

---

## System Architecture

![System Architecture](docs/v0.0.1workflow.png)

- One JSON file per grant
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
│
├── data/
│   ├── grants/
│   ├── processed_grants/
│   └── taxonomy/
│       ├── mission_tags.json
│       ├── population_tags.json
│       ├── org_types.json
│       ├── geography_tags.json
│       ├── red_flag_tags.json
│       ├── schema_version.json
│       ├── changelog.md
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
│   └── grant_profile_build.md
│
├── pipeline/
│   ├── __init__.py
│   ├── config.py
│   ├── cke.py
│   ├── canonical_mapper.py
│   ├── embedding_matcher.py
│   ├── grant_profile_builder.py
│   └── build_taxonomy_embeddings.py
│
└── prompts/
    └── cke_prompt_v1.txt
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
  - `CKE_PROMPT_PATH` (default: `prompts/cke_prompt_v1.txt`)
  - `TAXONOMY_DIR` (default: `data/taxonomy/`)
  - `TAXONOMY_EMBEDDINGS_DIR` (default: `data/taxonomy/embeddings/`)
  - `SCHEMA_VERSION_PATH` (default: `data/taxonomy/schema_version.json`)
  - `PROCESSED_GRANTS_DIR` (default: `data/processed_grants/`)
- Model names (override via env):
  - `OPENAI_CHAT_MODEL` (default: `gpt-4o-mini`)
  - `OPENAI_EMBEDDING_MODEL` (default: `text-embedding-3-small`)
  - `TOP_K` (default: `5`)
  - `THRESHOLD_MISSION` (default: `0.45`)
  - `THRESHOLD_POPULATION` (default: `0.50`)
  - `THRESHOLD_ORG_TYPE` (default: `0.50`)
  - `THRESHOLD_GEOGRAPHY` (default: `0.55`)
  - `THRESHOLD_RED_FLAGS` (default: `0.35`)
  - `THRESHOLD_DEFAULT` (default: `0.51`)
  - `TIMEZONE` (default: `America/New_York` for `created_at` timestamps)

---

## Makefile Shortcuts

Use the provided Make targets to keep taxonomies in sync:

- Rebuild embeddings for all taxonomies (force):
  - `make rebuild-taxonomy`
- Validate taxonomy lists vs. embeddings (strict):
  - `make validate-taxonomy`
- Rebuild then validate in one go:
  - `make taxonomy-refresh`

These commands assume `.env` contains `OPENAI_API_KEY` (auto‑loaded by the pipeline).

---

## Data Design

Grant JSON Structure

Each grant lives in its own JSON file:

```json
{
  "grant_name": "",
  "grant_org": "",
  "link": "",

  "mission_tags": [],
  "population_tags": [],
  "org_type_tags": [],
  "geography_tags": [],

  "funding_range": { "min": 0, "max": 0 },
  "deadline_type": "",

  "eligibility_notes": "",
  "red_flags": []
}
```

This format is:
- Interpretable
- LLM-friendly
- Easy to maintain
- Scalable for a website

---

## Taxonomy (Education-Focused)

EduGrant AI uses a hand-curated education taxonomy (not clustering). This ensures consistent and meaningful matching.

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

EduGrant AI eliminates this waste by showing nonprofits exactly which NSF programs fit — and which do not.

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

EduGrant AI fills this gap by providing public, transparent, and legally permissible grant intelligence that NSF itself cannot provide.

---

### How EduGrant AI Helps in a High-Competition, High-Uncertainty NSF Landscape

EduGrant AI provides:
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

The funding is still there — but only for organizations who apply intelligently. EduGrant AI helps them do exactly that.

---

## How to Use This Repo

1. Install and set env

   - `pip install -r requirements.txt`
   - `.env` with `OPENAI_API_KEY=...`

2. Add new grants

   Create a JSON file in: `data/sample_grants/`

3. Add nonprofit org profiles

   Place JSON files in: `data/sample_org_profiles/`

4. Run matching

   Use: `notebooks/matching_engine_demo.ipynb`

5. Generate reports

   Use: `notebooks/demo_report_generator.ipynb`

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

See docs/grant_profile_build.md for the detailed steps.

---

## Future Roadmap

- Lightweight FastAPI backend
- Website for nonprofits to paste mission statements
- Auto-ingest RFP URLs for structured extraction
- "Grant alerts" based on mission alignment
- Multi-tenant nonprofit profile storage

---

## Mission

EduGrant AI’s mission is to support small education nonprofits that often lack staff, capacity, and grant-writing resources. By providing transparent, trustworthy funding intelligence, EduGrant AI helps democratize access to education funding.
