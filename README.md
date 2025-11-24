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

---

## Why Not Just Use ChatGPT?

![Why use EdGrant AI instead of ChatGPT?](<docs/Why EdGrantAI.png>)

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

![System Architecture](docs/workflow.png)

- One JSON file per grant
- One JSON profile per nonprofit
- Matching is transparent and explainable

---

## Repository Structure

```
EdGrantAI/
│
├── README.md
│
├── data/
│   ├── taxonomy/
│   │   ├── mission_tags.json
│   │   ├── population_tags.json
│   │   ├── org_types.json
│   │   ├── geography_tags.json
│   │   └── red_flag_tags.json
│   │
│   ├── sample_grants/
│   └── sample_org_profiles/
│
├── notebooks/
│   ├── org_tag_extractor.ipynb
│   ├── grant_rfp_extraction.ipynb
│   ├── matching_engine_demo.ipynb
│   └── demo_report_generator.ipynb
│
├── src/
│   ├── extract/
│   ├── match/
│   ├── generate/
│   ├── database/
│   └── utils/
│
├── examples/
│   ├── Grant_Fit_Report_Literacy_Org.pdf
│   └── pipeline_overview.png
│
└── docs/
```

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

## How to Use This Repo

1. Add new grants

   Create a JSON file in: `data/sample_grants/`

2. Add nonprofit org profiles

   Place JSON files in: `data/sample_org_profiles/`

3. Run matching

   Use: `notebooks/matching_engine_demo.ipynb`

4. Generate reports

   Use: `notebooks/demo_report_generator.ipynb`

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


