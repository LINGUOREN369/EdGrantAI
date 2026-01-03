# Extraction

This document explains how EdGrantAI extracts evidence from raw text before any taxonomy mapping or scoring.

---

## Controlled Keyphrase Extractor (CKE)

Purpose:
- Extract short, verbatim phrases from raw text.
- Avoid inference or paraphrase.

Key constraints:
- Phrases must appear exactly in the source text.
- Typical length is 1 to 6 words.
- Output is a strict JSON array of strings.

Where it lives:
- Prompt: `prompts/cke_prompt_nsf_v1.txt`
- Code: `extraction/cke.py`

Example output:

```json
[
  "robotics clubs",
  "maker labs",
  "middle school students",
  "first-generation youth"
]
```

---

## Deterministic metadata extraction

Grant-specific metadata is extracted with deterministic parsers to avoid hallucination:
- Deadlines are parsed from the raw text and normalized when possible.
- Status is classified as `date`, `multiple`, `rolling`, or `unspecified`.
- Raw deadline mentions are retained for review.

Relevant code:
- `extraction/deadline_extractor.py`

---

## Outputs

Extraction produces:
- `extracted_phrases` (verbatim phrases)
- Deadline metadata for grant profiles

These outputs are inputs to the mapping and profile-building stages.

---

## Where to go next

- Profile building: `docs/02_profile_building.md`
- Matching algorithm and formula: `docs/03_matching_algorithm_and_formula.md`
