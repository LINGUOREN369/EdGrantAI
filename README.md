EduGrant AI

A lightweight, transparent, and high-impact grant-matching system for small education nonprofits.

⸻

Overview

EduGrant AI helps small education nonprofits quickly understand:
	•	Which grants fit their mission?
	•	Which grants they are actually eligible for?
	•	Which grants they should NOT waste time applying to?
	•	Why a grant is or is not a good match?

Instead of giving nonprofits a random list of grants (like ChatGPT would), EduGrant AI provides:
	•	structured, explainable matching
	•	taxonomy-driven tagging
	•	curated evergreen education grants
	•	eligibility analysis & red flags
	•	clear Grant Fit Reports

EduGrant AI is built to be low-maintenance and high-impact — ideal for small education nonprofits with limited staff and no full-time grant writers.

⸻

Why Not Just Use ChatGPT?

Nonprofits can ask ChatGPT for a list of grants.
But ChatGPT gives:

❌ one-off suggestions
❌ hallucinated grants
❌ expired deadlines
❌ no eligibility validation
❌ no mission alignment scoring
❌ no consistent criteria
❌ no long-term strategy

EduGrant AI is fundamentally different:

✔ Uses a curated education-specific taxonomy
✔ Extracts structured JSON from RFPs
✔ Evaluates mission alignment
✔ Checks eligibility & geography requirements
✔ Detects “red flags” (e.g., must have district partner)
✔ Produces transparent, repeatable Grant Fit Reports

⸻

System Architecture

 Nonprofit Mission Text
            │
            ▼
  Org Profile Extractor (LLM)
            │
            ▼
   Organization Profile JSON
            │
            ▼
     Matching Engine ───────────┐
            │                    │
            ▼                    │
  Grant Knowledge Base (JSON) ◄──┘
            │
            ▼
     Grant Fit Report (PDF/JSON)

	•	One JSON file per grant
	•	One JSON profile per nonprofit
	•	Matching is transparent and explainable

⸻

Repository Structure

EduGrant-AI/
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
│   ├── sample_grants/        ← One JSON per grant
│   └── sample_org_profiles/  ← One JSON per nonprofit
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


⸻

Data Design

Grant JSON Structure

Each grant lives in its own JSON file:

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

This format is:
	•	interpretable
	•	LLM-friendly
	•	easy to maintain
	•	scalable for a website

⸻

Taxonomy (Education-Focused)

EduGrant AI uses a hand-curated taxonomy rather than clustering.
This ensures consistent, meaningful matching.
	•	mission_tags: literacy, STEM, learning recovery, teacher PD, education equity, EdTech, etc.
	•	population_tags: low-income, ELL, disabilities, BIPOC, rural, K–3, HS
	•	org_type_tags: nonprofit, school district, university, CBO
	•	geography_tags: US National, state-specific, global
	•	red_flag_tags: “requires district partner,” “invitation-only,” etc.

⸻

Matching Engine

A transparent scoring system based on:

Mission Alignment     50%
Eligibility Fit       40%
Geography Fit         10%

Outputs include:
	•	Ranked list of grants
	•	Matching rationale
	•	Eligibility issues
	•	Risk / red flag warnings
	•	Funding ranges & deadlines

⸻

Grant Fit Report

Each nonprofit receives:
	•	Top aligned grants
	•	Why they match
	•	Red flags
	•	Eligibility summary
	•	Recommended priority (apply / maybe / avoid)

This helps nonprofits avoid wasting 30–50 hours on ineligible grants.

⸻

How to Use This Repo

1. Add new grants

Create a JSON file in:

data/sample_grants/

2. Add nonprofit org profiles

Create JSON files in:

data/sample_org_profiles/

3. Run matching

Use:

notebooks/matching_engine_demo.ipynb

4. Generate reports

Use:

notebooks/demo_report_generator.ipynb


⸻

🌍 Future Roadmap
	•	Simple FastAPI backend to serve the JSON DB
	•	Website for nonprofits to paste mission statements
	•	Auto-ingest RFP URLs
	•	“Grant alerts” based on mission alignment
	•	Multi-tenant storage for nonprofits

⸻

❤️ Mission

EduGrant AI’s goal is to support small education nonprofits with limited time, staff, and grant-writing capacity by providing transparent, trustworthy, and easy-to-maintain funding intelligence.
