# Responsible AI, Alignment, and Human Oversight (Case Study Review)

**Case Study: Moving Beyond Generic Chatbots to Reliable Decision Support**

For small education nonprofits, the grant landscape is often inequitable. Large institutions have dedicated teams to parse complex solicitation documents (RFPs), while smaller organizations rely on overworked staff who lose 10–100 hours on a single proposal depending on the size of the grant and often for grants they were never eligible for in the first place.

**EdGrantAI** was built to solve this specific problem. It is an evidence-bound decision engine that converts complex NSF solicitations into clear, actionable intelligence. This case study illustrates how nonprofits can move beyond "playing with ChatGPT" to building specialized, transparent tools that solve mission-critical problems.

---

## The Inspiration: Why We Built This

Nonprofits exist in a high-stakes environment where time is the scarcest resource. Access to private funding is often relationship-driven and invite-only. Public funding (for example, National Science Foundation) is open to all but buried under technical jargon, shifting deadlines, and complex eligibility rules. Furthermore, federal agencies cannot legally "recommend" or rank grants for specific applicants.

We saw two major problems:

1. **The Resource Gap:** Small nonprofits cannot afford to manually scan thousands of pages of federal compliance documents.
2. **The AI Trap:** When nonprofits turn to general AI tools (like standard ChatGPT) for help, the AI often "hallucinates"—inventing grants that do not exist, misinterpreting deadlines, or providing generic advice that leads to rejection.

**Our Vision:** A tool that acts as a digital "Grant Officer"—one that does not sleep, does not guess, and shows its work for every recommendation.

---

## Case Study Review: Alignment, Ethics, and Oversight

This review explains how EdGrantAI embeds alignment, ethics, guardrails, and human oversight into the system. It also outlines how nonprofits can adapt these practices to build trustworthy tools that improve workflow efficiency.

---

## Alignment goals (system level)

EdGrantAI is designed to be:
- Evidence-bound (no invented facts)
- Transparent (traceable outputs and clear scoring)
- Reproducible (versioned taxonomy and deterministic parsing)
- Conservative in ambiguity (prefers "unknown" over guess)

These goals show up as concrete controls in extraction, mapping, profile building, and matching.

---

## Guardrails and ethics by pipeline stage

### 1) Extraction (Controlled Keyphrase Extractor)

Alignment choices:
- Extracts verbatim phrases only; no summarization or paraphrase.
- Output must be a strict JSON array; invalid output is rejected.
- Deadlines are handled by deterministic parsing, not the LLM.

Why it matters:
- Prevents hallucinated facts or invented deadlines.
- Keeps the system grounded in source evidence.

Code references:
- `extraction/cke.py`
- `extraction/deadline_extractor.py`
- `extraction/section_utils.py`

---

### 2) Mapping (Dictionary → Guardrails → Embeddings)

Alignment choices:
- Dictionary-first mapping for high-precision terms and synonyms.
- Embedding fallback is used only when dictionary matching fails.
- Section provenance restricts what can map to mission or red flags.
- Guardrails prevent common failure modes:
  - Audience phrases cannot create organization type tags.
  - Red flags require gating terms and, for grants, the Eligibility section.
  - Mechanism acronyms (REU, CAREER, etc.) cannot become mission tags.
  - Computing education requires explicit computing cues.
  - “English learners” requires the word “English.”

Why it matters:
- Avoids false eligibility claims.
- Prevents misclassification that could waste staff time.
- Constrains semantic similarity to safe, interpretable outcomes.

Code references:
- `mapping/canonical_mapper.py`
- `mapping/embedding_matcher.py`

---

### 3) Profile Building

Alignment choices:
- Profiles store evidence (`source_text` and `sources`) for every tag.
- Raw embeddings are not stored (data minimization).
- Taxonomy version and timestamps are recorded for auditability.
- Organization profiles apply stricter rules for precision:
  - Geography must be explicit or derived from a named state.
  - Grade-band tags are not inferred from generic “K-12.”
  - Red flags require multiple mentions and higher thresholds.

Why it matters:
- Maintains a clear audit trail.
- Limits sensitive or unstable data in storage.
- Reduces the chance of wrongful ineligibility or false positives.

Code references:
- `mapping/grant_profile_builder.py`
- `mapping/org_profile_builder.py`

---

### 4) Matching and Recommendations

Alignment choices:
- Confidence-weighted, symmetric overlap avoids bias from tag count.
- Red flags can hard-block if eligibility is unmet.
- Explanation generation is gated (top-K or minimum score).
- Deadline and funding extraction are re-checked against source text.

Why it matters:
- Prevents overconfident recommendations.
- Adds safety rails around eligibility and deadlines.
- Keeps explanations concise and grounded.

Code references:
- `matching/matching_engine.py`

---

## Responsible AI design principles in this repo

1) Evidence over creativity  
   - Everything traces to extracted text and curated taxonomy tags.

2) Transparency and reproducibility  
   - Profiles include taxonomy version, confidence values, and evidence.

3) Conservative defaults  
   - Strict thresholds and guarded embedding fallback.
   - “Unknown” is acceptable when evidence is missing.

4) Data minimization  
   - Raw embeddings are not stored in profiles.
   - Reports include only necessary metadata.

5) Human-in-the-loop control  
   - Humans curate the taxonomy, synonyms, and thresholds.
   - Humans decide whether to apply to a grant.

---

## Human role (required, not optional)

Humans control:
- Taxonomy content and synonyms (precision and scope)
- Thresholds, weights, and stoplists
- Source data quality and refresh cadence
- Final “Apply / Maybe / Avoid” decisions
- Evaluation and error analysis

The system provides evidence and ranking, but does not replace judgment.

---

## Alignment and ethics risks (and mitigations)

Potential risk: false eligibility recommendation  
Mitigations:
- Hard-block rules for eligibility red flags
- Guardrails and strict thresholds
- Manual review of high-stakes submissions

Potential risk: biased or incomplete taxonomy  
Mitigations:
- Human curation and change review
- Versioning for reproducibility
- Evaluation on real-world outcomes

Potential risk: data drift in source documents  
Mitigations:
- CSV refresh pipeline and reprocessing
- Explicit source URLs in profiles

Potential risk: over-reliance on AI explanations  
Mitigations:
- Explanation gating
- Evidence linked to tags and reasons
- Clear separation of explanation vs decision

---

## How this can inspire other nonprofits

Key takeaways for production tools:

1) Start with a narrow, high-impact workflow  
   - Pick one task where time loss is measurable (e.g., grant triage).

2) Build an evidence-first pipeline  
   - Extract verbatim evidence before using embeddings or LLMs.

3) Add guardrails early  
   - Prevent common errors before they reach users.

4) Make outputs auditable  
   - Show the chain from evidence → tag → score → recommendation.

5) Keep humans in control  
   - The tool should surface options, not decide outcomes.

6) Measure real impact  
   - Track time saved, reduction in wasted proposals, and quality of matches.

---

## Practical adoption path for nonprofits

Phase 1 (2–4 weeks):
- Ingest CSV or static documents.
- Build profiles and run baseline matching.
- Review outputs manually to tune taxonomy and thresholds.

Phase 2 (1–2 months):
- Add guardrails based on observed errors.
- Introduce explanation gating and reason strings.
- Formalize evaluation with a small labeled set.

Phase 3 (ongoing):
- Integrate into workflows (CRM, calendar, intake forms).
- Track time saved and acceptance rates.
- Expand taxonomy and sources only when quality remains stable.

---

## Summary

EdGrantAI is not a general chatbot. It is a constrained, evidence-driven system with explicit guardrails and human oversight. That combination makes it safer, more transparent, and more useful in nonprofit decision workflows.
