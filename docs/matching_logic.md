# Matching Logic

- Retrieval: SmartRetriever
  - Prefer metadata filtering (e.g., tags); if too few results, fall back to semantic retrieval
- Scoring: weighted_score(similarity, meta, project)
  - Semantic similarity (distance -> similarity)
  - Domain weights (STEM/EdTech/curriculum/PD)
  - Eligibility rule multipliers (501(c)(3)/geography)
- Output: grant_id, title, snippet, score, meta
