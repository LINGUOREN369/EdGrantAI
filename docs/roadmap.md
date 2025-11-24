# Roadmap

- Ingest
  - [ ] Support more PDF/HTML cleaning pipelines
  - [ ] Extract main content from web pages (remove navigation/ads)
- Extract
  - [ ] Introduce LLM JSON mode + function calling aligned with Pydantic schema
  - [ ] Strengthen date/amount parsing and funder extraction
- RAG
  - [ ] Joint index of structured fields + source paragraphs
  - [ ] Smarter construction of metadata filters
- Matching
  - [ ] Refine subject/grade weights; introduce learned regression weights
  - [ ] Batch deduplication and same-source aggregation
- Reasoning
  - [ ] Add verifiable citations (paragraph numbers/links)
  - [ ] Draft outreach emails/application outlines
- API/UI
  - [ ] Add pagination and caching
  - [ ] Improve frontend interactions and metric displays
