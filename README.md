# EdGrant AI~

## 1. Mission: Make Education Funding Fair, Transparent, and Accessible—Especially for Small Nonprofits

EduGrant AI exists because education funding is becoming less stable, more competitive, and increasingly dominated by private actors. As public dollars decline, education nonprofits must rely on foundations, CSR programs, and individual philanthropists, but these opportunities are scattered across PDFs, poorly indexed, filled with jargon, and time-consuming to interpret. Large organizations have development teams to manage this complexity. Small education nonprofits do not. My mission is to bring structure, transparency, and equity to this landscape—and to ensure that smaller organizations are not left behind.

## 2. Why I Started: A Direct Encounter With the Crisis

EduGrant AI was born from lived experience. I lost a post-graduation role because the grant funding behind it collapsed. Friends in teaching, research, and graduate programs faced similar cuts. During my nonprofit consulting work, I saw how even established organizations struggle—but for small education nonprofits, the situation is far worse. When a small team has no grant writer, no analyst, and no slack time, each funding shift becomes existential. The problem is structural: public funding is retreating, private funding is opaque, and small teams lack the tools to navigate it. EduGrant AI fills this gap by giving small organizations the intelligence they cannot afford to build.

## 3. Why I’m Starting With Education

Education is the sector where funding volatility hits hardest: district budgets fluctuate; higher ed reduces research; STEM and curriculum nonprofits rely on irregular grants; foundations and CSR priorities shift quickly; and HWIs fund niche interests. Small education nonprofits are forced to compete for the same pool of opportunities as major universities, large edtech companies, and national organizations—without comparable staff capacity. This sector urgently needs AI-powered funding support tailored to small teams. That’s why education is my starting point.

## 4. The Insight That Made EduGrant AI Necessary

My background showed me a sharp contrast. In hedge funds, AI and ML are used heavily for pattern recognition, matching, and decision support. In education nonprofits—especially small ones—funding decisions still depend on manually reading PDFs and guessing alignment. At the exact moment when public funding declines and private funding becomes essential, small nonprofits have the least capacity to adapt. EduGrant AI is built on a simple belief: if small education organizations must operate in a complex, competitive funding environment, they deserve the same analytical power that sophisticated institutions use.
  
## 5. Purpose: Technology as a Tool, Equity as the Mission

EduGrant AI is not just a tool—it is a response to a changing reality: fewer public dollars, more private influence, opaque grant descriptions, and more organizations chasing limited resources. For small, under-resourced education nonprofits, this isn’t just inefficient—it’s inequitable. EduGrant AI exists to help these organizations reclaim time, make informed decisions, and access opportunities that would otherwise remain hidden. Technology is my method. Equity—and the survival of small education nonprofits—is my mission.

---

## System Workflow

```
┌──────────────────────────────────────────────────────────┐
│                      EdGrant AI System                   │
└──────────────────────────────────────────────────────────┘

                       USER INPUT
     (Nonprofit project description, question, draft text)
                                 │
                                 ▼

                 ┌──────────────────────────────┐
                 │  1. RFP Structurer Agent     │
                 │   (LLM-assisted extractor)   │
                 └──────────────────────────────┘
                - Clean RFP text
                - Extract eligibility
                - Extract deadlines / award size
                - Extract focus areas
                - Fill GrantSchema JSON
                                 │
                                 ▼

                 ┌──────────────────────────────┐
                 │   2. RFP Chunker & Embedder  │
                 │   (semantic + metadata)      │
                 └──────────────────────────────┘
                - Chunk RFP into sections
                - Generate embeddings
                - Store in vector DB
                                 │
                                 ▼

┌──────────────────────────────────────────────────────────┐
│                   Vector Store (Chroma/Pinecone)          │
│     (chunks + metadata: eligibility, tags, funder, etc.)  │
└──────────────────────────────────────────────────────────┘
                                 │
                                 ▼

                 ┌──────────────────────────────┐
                 │  3. Matching Agent           │
                 │   (semantic + rules + RAG)   │
                 └──────────────────────────────┘
                - Retrieve RFP chunks relevant to nonprofit
                - Apply eligibility rules
                - Apply education-specific weights
                - Ranking with fallback RAG:
                   (Filtered Retrieval → Fallback Semantic Retrieval)
                                 │
                                 ▼

                 ┌──────────────────────────────┐
                 │ 4. Reasoning Agent           │
                 │   (LLM-guided explainer)     │
                 └──────────────────────────────┘
                Generates:
                - Why this grant is a fit
                - Eligibility concerns
                - Alignment with funder priorities
                - Evidence requirements summary
                - Recommended narrative angle
                                 │
                                 ▼

                 ┌──────────────────────────────┐
                 │     5. Results Composer      │
                 │   (UI-ready structured data) │
                 └──────────────────────────────┘
                Prepares output for:
                - Web UI
                - PDF report
                - Notion export
                - Email summary
                                 │
                                 ▼

                          USER SEES OUTPUT
```

---

## Architecture (Mermaid)

```mermaid
flowchart LR
  A[Ingest: HTML/PDF -> Clean] --> B[Extract: Structurer -> GrantSchema(JSON)]
  B --> C1[Chunker]
  C1 --> C2[Embedder]
  C2 --> C3[(Vector DB: Chroma/Pinecone)]

  subgraph Retrieval
    D1[Build Query] --> D2{Enough results with metadata filter?}
    D2 -- Yes --> D3[Filtered Retrieval]
    D2 -- No  --> D4[Fallback Semantic Retrieval]
  end

  C3 --> D1
  D3 --> E[Matching: similarity x rules x weights]
  D4 --> E
  E --> F[Reasoning: fit + risks + narrative]
  F --> G[Results Composer]
  G --> H[API/UI: FastAPI + UI MVP]
```

---

## Repository Structure

```
edgrant-ai/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   ├── raw/               # Raw RFP text (from ingest pipeline)
│   ├── structured/        # GrantSchema JSON (for embedding + matching)
│   ├── embeddings/        # Optional: cached vector store data
│   └── samples/           # Example nonprofit project descriptions
├── ingest/
│   ├── fetch_html.py      # Playwright webpage fetcher (foundations, ED, NSF)
│   ├── parse_pdf.py       # PDF → text
│   ├── clean_text.py      # Basic cleaning (headers/footers, spacing, noise)
│   └── pipeline.py        # URL/file → raw text → data/raw/
├── extract/
│   ├── schema.py          # GrantSchema (Pydantic): title/funder/eligibility/deadline/tags
│   ├── llm_structured.py  # RFP Structurer Agent (LLM-ready; heuristic fallback)
│   ├── regex_helpers.py   # Rule-based helpers (dates/amounts)
│   └── build_structured_dataset.py  # Batch: raw → GrantSchema JSON → data/structured/
├── rag/
│   ├── chunker.py         # Split structured/raw text into chunks
│   ├── embedder.py        # OpenAI embeddings (degrades gracefully if no API key)
│   ├── vector_store.py    # Chroma/Pinecone wrapper (here: Chroma)
│   ├── retriever.py       # Smart retrieval: metadata-filtered → fallback semantic
│   └── index_builder.py   # Build index from structured JSON
├── matching/
│   ├── scoring.py         # Score = semantic × rules × domain weights
│   ├── eligibility_rules.py# Rule engine: 501(c)(3), geography, small nonprofit hints
│   ├── vertical_weights.py# Weights for EdTech/STEM/curriculum/PD, etc.
│   ├── match_engine.py    # Matching Agent: retrieve → filter → rank
│   └── pipeline.py        # run_matching(project_description)
├── reasoning/
│   ├── templates/
│   │   ├── fit.md         # LLM template: why grant fits your org
│   │   ├── risks.md       # LLM template: eligibility risk
│   │   └── narrative_angle.md # LLM template: narrative angle suggestions
│   ├── llm_reasoner.py    # Reasoning Agent: fit/risks/angle from retrieved evidence
│   └── composer.py        # Compose UI-ready outputs
├── api/
│   └── main.py            # FastAPI: /match /explain /grant/{id} /health
├── ui-mvp/
│   ├── pages/
│   ├── components/
│   ├── styles/
│   └── public/
├── notebooks/
│   ├── matching_eval.ipynb
│   ├── rag_tests.ipynb
│   └── extraction_eval.ipynb
└── docs/
    ├── architecture.md     # Minimal agentic architecture (Mermaid)
    ├── schema.md
    ├── matching_logic.md
    └── roadmap.md
```

---

## Install & Setup

- Requirements: Python 3.10+
- Install deps: `pip install -r requirements.txt`
- Copy env: `cp .env.example .env` and fill values
  - `OPENAI_API_KEY` (optional; without it, local fallbacks are used)
  - `DATA_RAW_DIR`, `DATA_STRUCTURED_DIR`, `CHROMA_DB_DIR`, `VECTOR_COLLECTION`
- Playwright browsers (for HTML fetch): `python -m playwright install chromium`

## Quick Start

1) Ingest raw data
- From URL (HTML): `python -m ingest.pipeline https://example.com/rfp --kind html`
- From PDF: `python -m ingest.pipeline /path/to/file.pdf --kind pdf`

2) Structure into GrantSchema JSON
- `python -m extract.build_structured_dataset`

3) Build vector index
- `python -m rag.index_builder`

4) Run API
- `uvicorn api.main:app --reload`

## API Endpoints

- `GET /health` → `{ status: "ok" }`
- `POST /match` → `{ results: [...] }`
  - Body: `{ "project_description": "...", "top_k": 5 }`
- `POST /explain` → `{ grant_id, fit, risks, narrative_angles }`
  - Body: `{ "project_description": "...", "grant_id": "..." }`
- `GET /grant/{id}` → GrantSchema JSON

Example curl

- Match: `curl -X POST http://127.0.0.1:8000/match -H 'Content-Type: application/json' -d '{"project_description":"After-school STEM program...","top_k":3}'`
- Explain: `curl -X POST http://127.0.0.1:8000/explain -H 'Content-Type: application/json' -d '{"project_description":"...","grant_id":"<id>"}'`

## Tech Notes

- OpenAI usage is optional. Without `OPENAI_API_KEY`, the system degrades gracefully (zero-vector embeddings and echo-style reasoning) so the pipeline stays runnable.
- ChromaDB is used for local persistence; you can swap in Pinecone by replacing `rag/vector_store.py` with a Pinecone client wrapper.
- The RFP Structurer Agent can be upgraded to function-calling JSON alignment; see `extract/llm_structured.py` for the integration point.

## MVP Features

- RFP → structured GrantSchema (title/funder/eligibility/deadline/tags)
- RAG index over structured summaries; metadata-aware retrieval with fallback
- Matching that combines semantic similarity, eligibility rules, and education-specific weights
- Explanations: fit, risks, and narrative angles

## Roadmap & Architecture

- See `docs/architecture.md`, `docs/schema.md`, `docs/matching_logic.md`, and `docs/roadmap.md`.
- I can generate and refine a concise Mermaid agentic diagram on request.

## Responsible Use

This software assists with discovery and analysis; it does not replace grant guidelines. Always verify deadlines, amounts, and eligibility on the official funder site before applying.

---

© 2025 EduGrant AI — Template for equitable education funding intelligence.
