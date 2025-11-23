# Architecture

Concise agentic flow with explicit retrieval fallback and results composition.

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

Notes
- Ingest: Playwright for HTML, pdfplumber for PDF; normalized raw text.
- Extract: Structurer produces GrantSchema JSON (Pydantic) with eligibility, deadline, tags.
- Index: Chunk + embeddings persisted to vector store (Chroma by default).
- Retrieval: Try metadata-filtered first; if too few results, fall back to pure semantic retrieval.
- Matching: Combines similarity, lightweight eligibility rules, and education-specific weights.
- Reasoning: Generates fit, risks, narrative angles grounded in retrieved evidence.
- Results Composer: Packs outputs for API/UI, PDF, or other exports.
