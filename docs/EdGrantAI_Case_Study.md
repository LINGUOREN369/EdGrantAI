# EdGrantAI: Democratizing Access to Funding with Specialized AI

Note: Technical details are consolidated in `docs/architecture_design.md`, `docs/data_source_and_handling.md`, `docs/extraction.md`, `docs/profile_building.md`, and `docs/matching_algorithm_and_formula.md`. This case study focuses on narrative and impact.

  Case Study: Moving Beyond Generic Chatbots to Reliable Decision Support

  For small education nonprofits, the grant landscape is often inequitable. Large institutions have
  dedicated teams to parse complex solicitation documents (RFPs), while smaller organizations rely on
  overworked staff who lose 40–80 hours on a single proposal—often for grants they were never eligible for
  in the first place.

  EdGrantAI was built to solve this specific problem. It is an evidence-bound decision engine that converts
  complex NSF solicitations into clear, actionable intelligence. This case study illustrates how nonprofits
  can move beyond "playing with ChatGPT" to building specialized, transparent tools that solve mission-
  critical problems.

  The Inspiration: Why We Built This

  - Nonprofits exist in a high-stakes environment where time is the scarcest resource. Access to private
  funding is often relationship-driven and invite-only. Public funding (like the National Science
  Foundation) is open to all but buried under technical jargon, shifting deadlines, and complex eligibility
  rules.
  - Federal agencies cannot recommend or rank grants for individual applicants due to fairness and
  competition rules. Small orgs are left to navigate alone.
  - We saw two major problems:
      1. The Resource Gap: Small nonprofits cannot afford to manually scan thousands of pages of federal
  compliance documents.
      2. The AI Trap: General chatbots hallucinate, misread eligibility, surface expired items, and provide
  generic advice that doesn’t hold up.

  Our Vision: A tool that acts as a digital “Grant Officer”—one that doesn’t sleep, doesn’t guess, and
  shows its work for every recommendation.

  The Solution: A “Trust-First” Architecture
  Unlike a chatbot that writes creative poetry, EdGrantAI is designed to be an auditor. It follows a strict
  pipeline: Extraction → Mapping → Matching. Every recommendation is grounded in evidence found directly in
  the text, and “unknown” remains a valid state.

  - Phase 1: The Strict Librarian (Extraction)
      - The Challenge: Government RFPs are messy: HTML noise, disclaimers, and lengthy instructions.
      - Our Approach: A Controlled Keyphrase Extractor that pulls short, verbatim phrases about mission,
  scope, populations, eligibility cues, and requirements from the actual text. It does not summarize or
  invent. Deadline lines are handled separately by a deterministic parser; the extractor itself does not
  return dates.
      - If the text isn’t there, the system reports “Unknown” rather than guessing.
  - Phase 2: The Universal Translator (Dictionary, Embeddings, Evidence)
      - Step 1: Dictionary. Hand-curated education terms and synonyms map directly with 100% confidence.
      - Step 2: Embeddings. When phrases aren’t in the dictionary, a semantic similarity model recovers
  sensible paraphrases while respecting thresholds and guardrails.
      - Step 3: Audit Trail. The system never discards original text. Each tag is tied to the exact
  phrase(s) it came from, plus section provenance when available. Users see “why,” not just “what.”
  - Phase 3: Transparent Matching
      - The engine scores mission/population/geography overlap and checks org-type eligibility, then
  applies red-flag penalties or hard blocks where appropriate.
      - Result: An Apply / Maybe / Avoid verdict with reasons and, optionally, a concise explanation.

  Data Ingestion & Refresh

  - Sources include official NSF opportunities, NSF awards, curated CSVs, and direct solicitation pages.
  - Only program-relevant sections are kept (e.g., Introduction, Program Description, Award Information,
  Eligibility Information). Items missing core sections are filtered out.
  - Grants are refreshed regularly; profiles can be rebuilt in batch so nonprofits work from current
  information.

  Evidence & Provenance

  - Every canonical tag retains its verbatim evidence phrases.
  - Section-aware provenance gates how phrases can be used (e.g., eligibility phrases inform eligibility/
  red flags; they do not create mission tags).
  - Unknown remains permissible when evidence is not present.

  Guardrails & Thresholds

  - Audience terms (e.g., “students,” “teachers”) don’t produce organization types.
  - Mechanism acronyms (e.g., REU, CAREER) never create mission tags.
  - Red flags require gating cues (e.g., only/required/submission limits) and, when available, eligibility
  provenance.
  - Computing tags require explicit computing cues; “English learners” must include “English.”
  - Geography and red flags use strict similarity thresholds; other taxonomies may use strict→loose
  fallback once per phrase. Top‑K/Top‑1 controls prevent over-tagging.

  Mission Selection Logic

  - Generic boilerplate (e.g., “broadening participation,” “workforce pathways”) is demoted relative to
  program‑specific mission phrases found in Program Description/Introduction.
  - Signals used: section, repetition within the document, and whether a phrase also appears in the title.
  - Outcome: more precise “primary mission” tags; generic terms can be retained as secondary context.

  Organization Profiles (Precision Rules)

  - Grade-band suppression: “K–12” alone doesn’t expand to elementary/middle/high without explicit
  evidence.
  - Population tags (e.g., rural students, low-income students) require explicit textual cues.
  - Geography must be explicit (with conservative, coarse derivations allowed, like a single-state tag if a
  state is named).
  - Red flags for orgs require multiple mentions and higher confidence to avoid spurious blocks.
  - Org-type must reflect self-description; platform/edtech cues add appropriate org-type tags.

  Deadline Handling

  - A deterministic parser extracts clear “deadline lines,” normalizes to ISO dates when years are present,
  and classifies status as date/multiple/rolling/unspecified.
  - “Unknown” is retained when a precise date cannot be parsed; raw mentions are saved for review.

  Matching Engine

  - Scoring prioritizes:
      - Mission overlap (highest weight)
      - Population overlap (next highest)
      - Geography overlap (lower weight)
      - Org type match treated as an eligibility gate (binary), with red-flag penalty multipliers.
  - Hard blocks: If a red flag indicates “universities only,” “schools only,” “government entities only,”
  or “nonprofits only,” and the org doesn’t meet the requirement, the result is “Avoid.”
  - Semantic tag overlap: Uses taxonomy embeddings to recognize close matches, applying a similarity floor
  to ignore weak links.
  - Buckets: Apply, Maybe, Avoid thresholds are explicit and calibrated.

  Taxonomy & Synonyms Lifecycle

  - Education-focused taxonomy for mission, population, org type, geography, and red flags.
  - Curated synonyms handle high-precision acronyms and paraphrases; safe format-variant synonyms are auto-
  generated and merged.
  - Guidance: add to the dictionary when variants are unambiguous; rely on embeddings for ambiguous or
  context-dependent terms.
  - Validation ensures taxonomy lists and embeddings remain in sync.

  Reproducibility & Versioning

  - Each profile records a taxonomy version and timestamp (with timezone).
  - Deterministic classification settings and versioned prompts keep outputs stable and comparable over
  time.
  - Evidence spans and decisions form an audit trail.

  Outputs & Reports

  - For each opportunity: structured profile with canonical tags (and confidence), evidence phrases,
  deadline status/dates, and red flags.
  - For each nonprofit: a ranked list with Apply/Maybe/Avoid, reasons (overlaps and constraints),
  deadlines, and optional concise explanations.
  - Profiles store evidence and canonical tags; raw vectors are not stored.

  Why This Matters for Nonprofits

  1. Hallucination-Proof: The system never invents a deadline and always ties claims to verbatim evidence.
  2. Radical Efficiency: Teams avoid spending 40–80 hours on dead-end proposals; scanning and triage time
  drops meaningfully.
  3. Equity: A three-person nonprofit can operate with the analytical rigor of a large development office.

  Evaluation

  - Offline: precision/recall for eligibility and key fields; extraction F1; calibration of Apply vs
  historical wins.
  - Online: time saved per team/week; reduction in false-positive “Apply”; user accept/reject rates; source
  coverage.
  - Quality gates: outputs that lack required evidence or fail guardrails do not advance to an “Apply”
  verdict.

  Limitations & Governance

  - Coverage gaps where portals require logins or block scraping; curated CSV/API paths mitigate but don’t
  solve all cases.
  - Ambiguous solicitations still need human judgment; the system surfaces uncertainty rather than
  guessing.
  - ToS and privacy: honors site terms; avoids PII where possible; supports data minimization.
  - Governance: bias audits, explainability surfaces, and clear operator controls in the roadmap.

  Operational Efficiency

  - Cost/latency controls include precomputed taxonomy embeddings, caching, and batching calls.
  - The system only invokes models where needed; dictionary-first logic and thresholds reduce unnecessary
  calls.

  A Blueprint for Building Your Own Tools

  1. Define a Narrow Scope
      - Don’t “do fundraising”; extract hard eligibility from RFPs and score alignment transparently.
  2. Curate Your Knowledge (Taxonomy)
      - Human-in-the-loop curation of tags and synonyms pays long-term dividends. Use embeddings to cover
  the long tail.
  3. Demand Evidence, Not Creativity
      - Favor verbatim extraction and explicit “unknown” states. Guardrails trump fluency.
  4. Build for Transparency
      - Show the chain from evidence → tag → decision. Include deadlines as status + raw mentions, not
  guesses.
  5. Plan for Reproducibility
      - Version your taxonomy, thresholds, and prompts. Keep outputs diffable and auditable.

  Looking Forward

  - User Feedback Loops: Lightweight accept/reject signals to improve synonyms, rules, and thresholds.
  - Proposal Assistance (Guardrailed): Draft outlines grounded strictly in extracted evidence to avoid
  fabrication.
  - Coverage Expansion: Smarter update detection and broader funding sources.
  - Integrations: CRM/grants management, calendar/task sync, and a simple web UI for nonprofits.
  - Governance & Efficiency: Bias checks, explainability dashboards, and continued cost reductions via
  routing and caching.

  Clarifications

  - Synonym mapping (e.g., “young learners” → “K–12 students”) is constrained by explicit cues and
  thresholds; not all general phrases will map.
  - “Highlights the line in the PDF” means the system captures the exact verbatim mentions (including
  deadline lines) from the ingested text and references them in outputs; it does not modify the PDF itself.
