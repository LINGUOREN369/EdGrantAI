# EdGrant AI — Tagging Pipeline Overview

This document describes the full set of components and steps used by EdGrant AI to transform raw grant text into structured, auditable, canonical metadata. The pipeline is designed for accuracy, auditability, scalability, and strict safety (no hallucination).


```
                                ┌───────────────────────────┐
                                │       Nonprofit Input     │
                                │ (Grant text, RFP content) │
                                └───────────────┬───────────┘
                                                │
                                                ▼
                           ┌──────────────────────────────────────────┐
                           │      1. Controlled Keyphrase Extractor   │
                           │------------------------------------------│
                           │  prompt: prompts/cke_prompt_nsf_v1.txt   │
                           │  code:   pipeline/cke.py                 │
                           └───────────────────────┬──────────────────┘
                                                   │  extracted_phrases
                                                   ▼
                     ┌────────────────────────────────────────────────────────┐
                     │        2. Dictionary + Embedding Mapping               │
                     │--------------------------------------------------------│
                     │ taxonomy JSON files: data/taxonomy/*.json              │
                     │ synonyms: data/taxonomy/synonyms/*.json (curated)     │
                     │ code: pipeline/embedding_matcher.py                    │
                     │      pipeline/canonical_mapper.py                      │
                     └──────────────────────────┬─────────────────────────────┘
                                                │ canonical_tags + confidence
                                                ▼
                   ┌──────────────────────────────────────────────────────────────┐
                   │             3. Grant Profile Builder                         │
                   │--------------------------------------------------------------│
                   │ code: src/pipeline/grant_profile_builder.py                  │
                   │ merges:                                                      │
                   │   - extracted phrases                                        │
                   │   - canonical tags                                           │
                   │   - taxonomy version                                         │
                   └──────────────────────────────┬───────────────────────────────┘
                                                  │ final structured JSON
                                                  ▼
                     ┌────────────────────────────────────────────────────────┐
                     │         Output: Processed Grant Profiles               │
                     │--------------------------------------------------------│
                     │ saved to: data/processed_grants/ (you can create)      │
                     │ e.g.,                                                │
                     │   data/processed_grants/grant_0001_profile.json        │
                     └────────────────────────────────────────────────────────┘

```


---

## System Principles

EdGrant AI follows three core architectural principles:

1. Extractive First (No Inference)

The system begins with verbatim extraction from text.
No guessing, no interpretation, no rewriting.

2. Evidence-Based Canonical Mapping

Canonical tags are assigned only when supported by extracted evidence and confirmed by semantic similarity.

3. Fully Auditable JSON Output

Every canonical tag is associated with:
    - the exact source phrase
    - similarity confidence
    - taxonomy version

This ensures transparency and reproducibility.

---

## 2. Pipeline Summary

Raw Grant Text
      ↓
(1) Controlled Keyphrase Extractor (Extract Verbatim)
      ↓ extracted_phrases
(2) Embedding-Based Semantic Mapping
      ↓ canonical tag + confidence
(3) Canonical Tag Assignment (Evidence-Linked)
      ↓
Final JSON Grant Profile


---

## 3. Controlled Keyphrase Extractor (CKE)

The Controlled Keyphrase Extractor is a restricted, rule-driven extraction module that uses:
    - a stored prompt file (/prompts/cke_prompt_nsf_v1.txt)
    - a Python execution wrapper (pipeline/cke.py)

Purpose

To extract short, meaningful, verbatim keyphrases from grant descriptions.

Key Constraints
    - Phrases must appear exactly in the text.
    - Length must be 1–6 words.
    - No inference, no synonyms, no canonical tags.
    - Extract only:
      - program or activity phrases
      - learning environments
      - population groups
      - explicit partners or roles
      - meaningful noun phrases

Example Output

```json
[
  "robotics clubs",
  "maker labs",
  "middle school students",
  "girls",
  "first-generation youth"
]
```

This stage ensures safety, interpretability, and non-hallucinatory behavior.

---

## 4. Dictionary + Embedding Mapping

Mapping uses two stages plus guardrails:
1) Dictionary pre-mapping (case/space/punctuation-insensitive):
   - Direct match against canonical tags and curated synonyms in `data/taxonomy/synonyms/`.
   - Matches map at confidence 1.0 and skip embeddings.
   - Synonyms are curated; safe auto variants are merged into curated files by `make synonyms-build` and `*.auto.json` are deleted.
2) Guardrails:
   - Block audience-like phrases mapping to org types; require gating terms for red flags; require explicit computing/English cues for certain tags.
3) Embedding fallback (strict → optional loose):
   - If no dictionary match, embed the phrase and compare to canonical tag embeddings.
   - Apply strict thresholds per taxonomy; if no match, a single looser pass for select taxonomies (geography/red flags remain strict by default).

Mapping is performed using semantic similarity:

`similarity(extracted_phrase_vector, canonical_tag_vector)`

The highest-scoring canonical tag above a threshold is selected.

Benefits
    - High precision via dictionary matches for common variants
    - Recall preserved via controlled embedding fallback
    - Guardrails reduce systemic misclassification (e.g., audience ≠ org type; gated red flags; explicit computing/English cues)

See also: `docs/mapping_funnel.md` for the full funnel and curation policy.

Example Mappings

| Extracted Phrase        | Canonical Tag                    | Confidence |
|-------------------------|----------------------------------|------------|
| robotics clubs          | robotics_education               | 0.92       |
| maker labs              | maker_education                  | 0.89       |
| middle school students  | middle_school_6_8_students       | 0.97       |
| girls                   | girls_and_young_women_students   | 0.84       |


---

## 5. Canonical Tag Assignment

Each mapped tag includes:
    - tag (canonical taxonomy ID)
    - source_text (verbatim evidence)
    - confidence (semantic similarity score)
    - taxonomy_version

This ensures full traceability and auditability.

---

## 6. Final JSON Output Structure

Below is an example output for a single processed grant:

```json
{
  "grant_id": "grant_0001",
  "taxonomy_version": "0.1.0",

  "extracted_phrases": [
    "robotics clubs",
    "maker labs",
    "middle school students",
    "girls",
    "first-generation youth"
  ],

  "canonical_tags": {
    "mission_tags": [
      {
        "tag": "robotics_education",
        "source_text": "robotics clubs",
        "confidence": 0.92
      },
      {
        "tag": "maker_education",
        "source_text": "maker labs",
        "confidence": 0.89
      }
    ],
    "population_tags": [
      {
        "tag": "middle_school_6_8_students",
        "source_text": "middle school students",
        "confidence": 0.97
      },
      {
        "tag": "girls_and_young_women_students",
        "source_text": "girls",
        "confidence": 0.84
      },
      {
        "tag": "first_generation_students",
        "source_text": "first-generation youth",
        "confidence": 0.90
      }
    ]
  }
}
```

This structure is optimized for search, ranking, filtering, analytics, and downstream application use.

---

## 7. File Locations in the Repository

| Component                | Location                      |
|--------------------------|-------------------------------|
| CKE Prompt               | prompts/cke_prompt_nsf_v1.txt |
| CKE Runner Code          | pipeline/cke.py               |
| Embedding Matching Code  | pipeline/embedding_matcher.py |
| Canonical Tag Mapper     | pipeline/canonical_mapper.py  |
| Taxonomy Files           | data/taxonomy/*               |
| Synonyms                 | data/taxonomy/synonyms/*      |
| This Document            | docs/Tagging Pipeline Overview.md |


---

## 8. Versioning Strategy
    - Taxonomy versions are stored in data/taxonomy/schema_version.json.
    - Prompts are versioned as separate files (*_v1.txt, *_v1.1.txt, etc.).
    - Pipeline code is tracked via Git version control.

This ensures stability, reproducibility, and transparent evolution of the system.

---

## 9. System Benefits
    - Zero hallucination (extractive-first design)
    - Strong auditability (every tag has evidence)
    - Semantic intelligence (embedding-based mapping)
    - Transparent and reproducible tagging
    - Modular and scalable architecture
    - Aligns with production standards used in systems such as PubMed MeSH, Semantic Scholar, and LinkedIn Ontology
