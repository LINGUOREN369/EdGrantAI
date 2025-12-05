# ORG PROFILE EXTRACTION — RULES SUMMARY (v0.0.10+)

These rules apply when building organization profiles (pipeline/org_profile_builder.py). They refine dictionary/embedding outputs with explicit evidence checks and stricter thresholds for higher precision.

## 1. DICTIONARY-FIRST LOGIC
- If exact or synonym match exists for org_type, population, geography, or mission:
  → assign tag with confidence = 1.0
  → skip embeddings for that category.
- If org name/text contains a U.S. state → tag single state as geography.

## 2. STRICT GEOGRAPHY RULES
- Only include geography if:
  (a) explicitly stated in text, OR
  (b) derived from org name/text (state-level only), OR
  (c) explicitly included by metadata.
- Do NOT include global/subnational geography unless text contains a direct reference.

## 3. MISSION TAG FILTERS
- Reject tags in these categories unless the text contains explicit evidence:
  - after-school STEM programs
  - out-of-school STEM programs
  - informal STEM learning
  - STEM career pathways
- Block these tags if confidence < 0.75 OR missing explicit signal words.

## 4. GRADE-BAND SUPPRESSION
- If text mentions only “K–12”, allow ONLY:
    → “K-12 STEM education”
- DO NOT generate:
    → elementary, middle school, or high school STEM education
  unless grade-level terms appear explicitly.

## 5. POLICY TAG REQUIREMENT
- Only allow “STEM education policy” when text includes:
    “policy”, “advocacy”, “legislation”, “statewide policy”, or similar.
- Otherwise block the tag even if embedding confidence is high.

## 6. POPULATION RULES
- “rural students,” “underserved communities,” “low-income students” allowed only if explicitly stated.
- School districts should NOT be included as population; use partner_tags if needed (not modeled here).

## 7. THRESHOLDS BY CATEGORY (ORG PROFILES)
- mission_tags:       ≥ 0.70
- population_tags:    ≥ 0.65
- org_type_tags:      ≥ 0.75
- geography_tags:     ≥ 0.85 unless explicit
- red_flags:          ≥ 0.80 AND must appear twice

## 8. LLM VALIDATION PASS (HEURISTICS)
Before finalizing, we:
- remove tags lacking explicit textual support if they belong to any restricted category
- ensure org_type is consistent with self‑description (e.g., edtech/platform)
- deduplicate synonyms (evidence aggregated per tag)

Implementation notes
- Guardrails and post‑filters live in `pipeline/org_profile_builder.py`.
- Dictionary vs embeddings funnel described in `docs/mapping_funnel.md`.

