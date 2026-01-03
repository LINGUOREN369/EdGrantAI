# Matching Engine Scoring (Transparent Example)

This document explains how the matching engine in `matching/matching_engine.py` computes scores, including the exact formula and a worked example.

---

## What the engine uses

For each organization and grant profile:
- `canonical_tags` for each taxonomy
- Each tag includes a `confidence` value in the range 0.0 to 1.0

Taxonomies used in scoring:
- Mission tags (semantic similarity with threshold)
- Population tags (semantic similarity with threshold)
- Organization type tags (exact match only)
- Geography tags (exact match only; "us_national" is treated as a full match)

Red flags:
- Some red flags hard-block eligibility.
- Otherwise a red-flag penalty multiplier is applied.

---

## Tag confidence handling

If a tag appears multiple times in the same profile, the engine keeps the **highest confidence** for that tag.

Confidence is used as a weight:
- A confidence of 1.00 gives full impact.
- A confidence of 0.50 gives half impact.

---

## Overlap formula (per taxonomy)

The engine computes a **symmetric confidence-weighted overlap**.

### Directional overlap (organization to grant)

For each organization tag, take the best matching grant tag:

```text
directional_overlap(organization -> grant) =
  sum over organization tags:
      organization_confidence * best_match_value
  divided by
      sum of organization_confidence values
```

Where:

```text
best_match_value = max over grant tags of:
    similarity(organization_tag, grant_tag) * grant_confidence
```

### Symmetric overlap

```text
symmetric_overlap =
  (directional_overlap(organization -> grant)
   + directional_overlap(grant -> organization)) / 2
```

### Similarity rules

- If embeddings exist for the taxonomy:
  - `similarity` is cosine similarity
  - if similarity is below the threshold and the tags are not identical, use 0
- If embeddings do not exist (or are not used for that taxonomy):
  - `similarity` is 1 for exact tag match, otherwise 0

---

## Final score formula

```text
score =
  mission_weight * symmetric_overlap(mission_tags)
+ population_weight * symmetric_overlap(population_tags)
+ organization_type_weight * symmetric_overlap(org_type_tags)
+ geography_weight * symmetric_overlap(geography_tags)

if red_flags_present:
  score = score * red_flag_penalty
```

Default weights live in `common/config.py`:
- Mission: 0.50
- Population: 0.40
- Organization type: 0.40
- Geography: 0.10

---

## Worked example

Assume:
- Similarity threshold = 0.50
- No red flags
- Default weights

### Organization tags (confidence)

Mission:
- STEM education (1.00)
- teacher professional learning (0.70)
- informal STEM learning (0.40)

Population:
- K-12 students (1.00)
- K-12 teachers (0.80)

Organization type:
- nonprofit_501c3 (1.00)

Geography:
- Maine (1.00)

### Grant tags (confidence)

Mission:
- science education (0.90)
- teacher development (0.60)

Population:
- K-12 teachers (1.00)
- undergraduate students (0.60)

Organization type:
- nonprofit_501c3 (0.70)
- higher_education_institution (0.50)

Geography:
- us_national (1.00)

### Mission similarity values (cosine)

- STEM education ↔ science education = 0.72
- teacher professional learning ↔ teacher development = 0.68
- informal STEM learning ↔ science education = 0.55
- All other pairs are below 0.50 and are ignored

---

### Step 1: Mission overlap

Organization -> grant:
- STEM education: 0.72 * 0.90 = 0.648
- teacher professional learning: 0.68 * 0.60 = 0.408
- informal STEM learning: 0.55 * 0.90 = 0.495

```text
numerator = (1.00 * 0.648) + (0.70 * 0.408) + (0.40 * 0.495)
          = 0.648 + 0.2856 + 0.198
          = 1.1316

denominator = 1.00 + 0.70 + 0.40 = 2.10

directional_overlap = 1.1316 / 2.10 = 0.539
```

Grant -> organization:
- science education: 0.72 * 1.00 = 0.72
- teacher development: 0.68 * 0.70 = 0.476

```text
numerator = (0.90 * 0.72) + (0.60 * 0.476)
          = 0.648 + 0.2856
          = 0.9336

denominator = 0.90 + 0.60 = 1.50

directional_overlap = 0.9336 / 1.50 = 0.6224
```

Symmetric mission overlap:
```text
(0.539 + 0.6224) / 2 = 0.5807
```

---

### Step 2: Population overlap

Only "K-12 teachers" matches.

Organization -> grant:
```text
numerator = (1.00 * 0) + (0.80 * 1.00) = 0.80
denominator = 1.00 + 0.80 = 1.80
directional_overlap = 0.80 / 1.80 = 0.444
```

Grant -> organization:
```text
numerator = (1.00 * 0.80) + (0.60 * 0) = 0.80
denominator = 1.00 + 0.60 = 1.60
directional_overlap = 0.80 / 1.60 = 0.50
```

Symmetric population overlap:
```text
(0.444 + 0.50) / 2 = 0.472
```

---

### Step 3: Organization type overlap (exact match)

Organization -> grant:
```text
directional_overlap = (1.00 * 0.70) / 1.00 = 0.70
```

Grant -> organization:
```text
numerator = (0.70 * 1.00) + (0.50 * 0) = 0.70
denominator = 0.70 + 0.50 = 1.20
directional_overlap = 0.70 / 1.20 = 0.5833
```

Symmetric organization type overlap:
```text
(0.70 + 0.5833) / 2 = 0.6417
```

---

### Step 4: Geography overlap

The grant has `us_national`, so geography overlap = 1.00.

---

### Step 5: Final score

```text
score =
  0.50 * 0.5807
+ 0.40 * 0.472
+ 0.40 * 0.6417
+ 0.10 * 1.00

score = 0.29035 + 0.1888 + 0.25668 + 0.10
score = 0.83583
```

If a red-flag penalty of 0.85 applies:
```text
final_score = 0.83583 * 0.85 = 0.710
```
