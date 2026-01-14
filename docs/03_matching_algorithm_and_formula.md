# Matching Algorithm and Formula

This document explains how scores are computed in `matching/matching_engine.py`, including the formula and a full worked example.

---

## Inputs to scoring

For each organization and grant profile:
- Canonical tags per taxonomy (with confidence scores)
- Red flags (for penalties and hard blocks)

Taxonomies used in scoring:
- Mission (semantic similarity)
- Population (semantic similarity)
- Organization type (exact match)
- Geography (exact match, with a "us_national" override)

---

## Overlap calculation (per taxonomy)

The engine computes a symmetric, confidence-weighted overlap.

Directional overlap (organization to grant):

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

Symmetric overlap:

```text
symmetric_overlap =
  (directional_overlap(organization -> grant)
   + directional_overlap(grant -> organization)) / 2
```

Similarity rules:
- If embeddings exist: cosine similarity, with a minimum threshold.
- If embeddings do not exist: exact match only (1 or 0).

Confidence handling:
- Tag confidence values are clamped to the range 0.0–1.0.
- If a tag appears multiple times, the highest confidence is used.

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

Default weights in `common/config.py`:
- Mission: 0.50
- Population: 0.40
- Organization type: 0.40
- Geography: 0.10

Hard blocks:
- Certain red flags enforce eligibility rules (for example: "universities_only").
- If the organization does not meet the required type, the score is forced to 0.

Buckets:
- `Apply` and `Maybe` thresholds are configurable in `common/config.py`.

---

## Recommendation output details

The recommendation report includes:
- Score, bucket, and overlap reasons
- Closest upcoming deadline (if found)
- Anticipated funding amount (verbatim, if found)
- Source URL

If `--explain` is enabled:
- Explanations are generated only for the top N or above a score threshold.
- A short synopsis is added when a “Synopsis:” line is found in source text.

Additional behaviors:
- Deadline extraction is retried from the source text if missing in the profile.
- Rolling deadlines are inferred from common “anytime” phrases in source text.

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

- STEM education <-> science education = 0.72
- teacher professional learning <-> teacher development = 0.68
- informal STEM learning <-> science education = 0.55
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

If a red-flag penalty of 0.95 applies:
```text
final_score = 0.83583 * 0.95 = 0.794
```
