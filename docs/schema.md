# GrantSchema

Core structured fields:

- id: Stable ID (based on text/URL hash)
- title: RFP title
- funder: Funder
- url: Detail or source link
- summary: Summary
- eligibility: Eligibility items (list)
- deadline: Deadline (optional)
- amount: Award amount or range (text)
- tags: Keywords, e.g., STEM/EdTech/K-12
- raw_ref: Traceback to original text location (optional)

Generation flow: raw text -> heuristics/LLM -> GrantSchema JSON -> data/structured/
