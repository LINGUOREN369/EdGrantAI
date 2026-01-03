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

Operational details:
- Uses the chat model from `common/config.py` (`OPENAI_CHAT_MODEL`).
- Strips fenced code blocks if the model wraps JSON in triple backticks.
- Raises a clear parse error if the output is not a JSON array.
- Initializes the OpenAI client lazily (only when the extractor is called).

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

Notes:
- The extractor does not guess missing years.
- It ignores “posted/published” lines that are not deadlines.

---

## Section provenance for phrases

Grant phrases are assigned to NSF sections so downstream mapping can enforce section-based rules.

Detected sections (case-insensitive, Roman numerals optional):
- Introduction
- Program Description
- Award Information
- Eligibility Information

If no heading is found, phrases are tagged as `Other`.

Relevant code:
- `extraction/section_utils.py`

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
