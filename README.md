# EdGrant AI

For small education nonprofits, the grant landscape is often inequitable. Large institutions have dedicated teams to parse complex solicitation documents (RFPs), while smaller organizations rely on overworked staff who lose 10–100 hours on a single proposal depending on the size of the grant and often for grants they were never eligible for in the first place.

EdGrantAI was built to solve this specific problem. It is an evidence-bound decision engine that converts complex NSF solicitations into clear, actionable intelligence. This case study illustrates how nonprofits can move beyond "playing with ChatGPT" to building specialized, transparent tools that solve mission-critical problems.

## What it does

- Builds structured grant and organization profiles from text
- Maps phrases to a curated education taxonomy
- Scores alignment with clear Apply / Maybe / Avoid buckets
- Surfaces eligibility constraints and red flags
- Produces JSON reports with ranked recommendations

## Quickstart

1) Install dependencies
- `pip install -r requirements.txt`
2) Set API key (for LLM explanations and embeddings)
- Create a `.env` file in the repo root and add:
  - `OPENAI_API_KEY=sk-...`
3) Build taxonomy embeddings (once)
- `make rebuild-taxonomy`
4) Process profiles
- `make grants-all`
- `make orgs-all`
5) Generate recommendations
- `make recs ORG=data/processed_orgs/<org>_profile.json [TOP=10]`
- `make recs-all`

## Documentation map

Start here for details and rationale:

- Architecture design: [docs/architecture_design.md](docs/architecture_design.md)
- Data source and handling: [docs/00_data_source_and_handling.md](docs/00_data_source_and_handling.md)
- Extraction: [docs/01_extraction.md](docs/01_extraction.md)
- Profile building: [docs/02_profile_building.md](docs/02_profile_building.md)
- Matching algorithm and formula: [docs/03_matching_algorithm_and_formula.md](docs/03_matching_algorithm_and_formula.md)
- Makefile commands: [docs/makefile_commands.md](docs/makefile_commands.md)
- Repository structure: [docs/repo_structure.md](docs/repo_structure.md)
- Responsible AI and alignment: [docs/responsible_ai_and_alignment.md](docs/responsible_ai_and_alignment.md)
- Backend deployment: [docs/backend_deployment.md](docs/backend_deployment.md)
- Case study: [docs/EdGrantAI_Case_Study.md](docs/EdGrantAI_Case_Study.md)
- Diagrams: [docs/structure.png](docs/structure.png), [docs/workflow.png](docs/workflow.png)

## Common commands

- Rebuild embeddings: `make rebuild-taxonomy`
- Validate embeddings: `make validate-taxonomy`
- Refresh taxonomy: `make taxonomy-refresh`
- Process all grants: `make grants-all`
- Process all orgs: `make orgs-all`
- Recommendations for one org: `make recs ORG=data/processed_orgs/<org>_profile.json [TOP=10]`
- Recommendations for all orgs: `make recs-all`

For the full list, see `Makefile`.

## Model choices (why these defaults)

- `gpt-4o-mini` for extraction and explanations: fast, low-cost, and strong at constrained JSON output when prompted; the task is extractive, not creative.
- `text-embedding-3-large` for semantic matching: robust similarity for short phrases and taxonomy tags with good quality-per-cost.

Both are configurable in `common/config.py` via environment variables.

## Configuration

Runtime settings are defined in `common/config.py` and can be overridden via environment variables or `.env`.

## Repository structure (high level)

- `data/` raw inputs, processed profiles, taxonomy, embeddings
- `extraction/` phrase extraction and source processing
- `mapping/` taxonomy mapping and embedding utilities
- `matching/` scoring and recommendations
- `prompts/` LLM prompts
- `reports/` output recommendation files
- `docs/` long-form documentation
