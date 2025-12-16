# EdGrantAI — Professor Brief + Email Draft

## One-Page Overview

EdGrantAI is a lightweight, open-source grant intelligence system designed for small education nonprofits. It structures unstructured RFP text into transparent, auditable profiles and ranks grant fit for a given organization with concise, evidence-based rationale.

Problem
- Small nonprofits face growing NSF competition and high application costs; they often apply without strong eligibility checks or alignment evidence.

Solution
- Deterministic, explainable pipeline that extracts verbatim phrases, maps them to a curated education taxonomy, and produces transparent “Apply/Maybe/Avoid” recommendations.

Why Now
- Competition for NSF programs is rising; agencies cannot recommend or pre-screen. A public, transparent, and ethical matching approach fills this gap.

Who Benefits
- Education nonprofits, RPPs, community colleges, and mission-aligned orgs that need rigorous but accessible decision-support.


## How It Works (Deterministic Pipeline)

- Extract (verbatim, no generation): `prompts/cke_prompt_nsf_v1.txt`, `pipeline/cke.py`
- Map (dictionary → embeddings with guardrails): `pipeline/canonical_mapper.py`, `pipeline/embedding_matcher.py`
- Build profiles (with deadlines, provenance): `pipeline/grant_profile_builder.py`, `pipeline/org_profile_builder.py`, `pipeline/deadline_extractor.py`
- Rank (transparent scoring + optional LLM bullets): `pipeline/matching_engine.py`, prompt in `prompts/matching_explainer_prompt_v1.txt`
- Configuration + thresholds: `pipeline/config.py`

Design choices
- Deterministic rules + curated taxonomy first; semantic fallback only when needed.
- Evidence-linked outputs (verbatim phrases + confidence + taxonomy version).
- Cost-optimized and Apache‑2.0 licensed for accessibility and equity.


## Live Demo Checklist (≈5 minutes)

Zero-setup artifacts to open
- Org profile (example): `data/processed_orgs/khan_profile.json`
- Grant profile (example): `data/processed_grants/nsf_REU_profile.json`
- Ranked recommendations (example): `reports/khan_recommendations.json`
- Workflow image: `docs/workflow.png`

Optional CLI (works without API key; explanations omitted)
- Re-rank for a sample org:
  - `make recs ORG=data/processed_orgs/khan_profile.json TOP=5`
  - Output (if OUT not provided): `reports/khan_recommendations.json`
- With explanations (requires `OPENAI_API_KEY`):
  - `make recs ORG=data/processed_orgs/khan_profile.json TOP=5 OUT=reports/khan_recommendations.json`

Build end-to-end (requires `OPENAI_API_KEY`)
- `make rebuild-taxonomy`
- `make grants-all`
- `make orgs-all`


## Responsible AI Choices

- Deterministic, rule-based reasoning for explainability and auditability.
- Verbatim extraction only; no hallucination or content generation.
- Curated, education-focused taxonomy with explicit guardrails (dictionary-first; gated red flags; org-type and computing tag constraints).
- Transparent scoring and evidence-linked outputs for human review.
- Apache‑2.0 license; low-cost, replicable tooling.


## Research/Teaching Fit

- Practical, principled AI case study: governance, thresholds, error budgets, and reproducibility.
- Cross-disciplinary modules: extraction prompts, ontology design, matching logic, evaluation pipelines.
- Extensible: program-aware NSF analysis, streaming updates, FastAPI/UX front end.

Key references
- Overview: `README.md`
- Pipeline details: `docs/grant_profile_build.md`
- Org rules: `docs/org_profile_rules.md`
- Mapping funnel: `docs/mapping_funnel.md`
- Prompts: `prompts/cke_prompt_nsf_v1.txt`, `prompts/matching_explainer_prompt_v1.txt`


## Email Draft

Dear Professor [Director's Last Name],

I hope this message finds you well. I’m writing as a student who took both your Cognitive Architecture and AI Ethics. Those discussions on the role of human judgment in computational systems have stayed with me and directly inspired the path I’ve taken since.

My starting point was a quant researcher internship at a high performing hedge fund, where I was immersed in a world defined by **extreme model governance, reproducibility, and tight error constraints.** The discipline was formative—it shaped my understanding of how rigorous frameworks can clarify complex decisions.

Yet, it was my subsequent pivot into nonprofit consulting and education technology that revealed a critical gap. I began working with organizations making mission-critical choices—about funding, programs, and community partnerships—often without access to _any_ of the analytical infrastructure I had come to see as essential. The disconnect was stark: the sectors tasked with some of our most human-centric challenges were operating with the least decision-support.

This contrast moved me from observation to action. I started building **EdGrantAI**—an open-source framework that seeks to apply quantitative rigor to social impact. It is designed not to automate human judgment, but to **structure information with transparency and logic**, enabling leaders to focus on strategy, ethics, and context.

The system embodies principles central to our seminar discussions:

- **Deterministic, rule-based reasoning** to ensure explainability and auditability.
- **Fine-tuned semantic models** that interpret mission and need, rather than generate content.
- **A cost-optimized, Apache 2.0-licensed architecture** built for equity and accessibility.

Now that the prototype is fully functional, I see its potential not just as a tool, but as a **practical framework for responsible AI**—one that could serve as a foundational case study and research platform for the Hastings Initiative. It represents a concrete example of how human-centered, ethically-grounded systems can be built for public benefit.

I am not seeking resources, but rather your **strategic perspective**. I have developed this project independently and am prepared to contribute it to Bowdoin. My goal is to refine it into an open, teachable resource that could support cross-disciplinary inquiry and help position RHI as a leader in practical, principled AI.

Might you be open to a brief conversation in the coming weeks? I would be grateful for the opportunity to walk you through the system and explore how it might align with the Initiative's vision.

Thank you for your inspiring teaching and guidance.

Sincerely,

[Your Name]
