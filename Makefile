.PHONY: rebuild-taxonomy validate-taxonomy taxonomy-refresh help grants-all orgs-all recs recs-all nsf-download nsf-awards-download nsf-opps-download nsf-from-csv grants-batch grants-refresh e2e

# Defaults for matching engine
GRANTS_DIR ?= data/processed_grants
ORGS_DIR ?= data/processed_orgs
TOP ?= 10

help:
	@echo "Available targets:"
	@echo "  rebuild-taxonomy     Rebuild embeddings for all taxonomies (force)"
	@echo "  validate-taxonomy    Validate taxonomy lists vs. embeddings (strict)"
	@echo "  taxonomy-refresh     Rebuild then validate (reliable one-liner)"
	@echo "  grants-all           Process all grant text files in data/grants"
	@echo "  orgs-all             Process all org text files in data/orgs"
	@echo "  recs                 Rank grants for one org (make recs ORG=<path>)"
	@echo "  recs-all             Rank grants for all org profiles in $(ORGS_DIR)"
	@echo "  synonyms-build       Auto-generate synonyms for all taxonomies (safe variants)"
	@echo "  e2e                  End-to-end: taxonomy refresh, grants refresh, batch build, orgs, recs"
	@echo "  nsf-download         Download NSF opportunities into data/grants (via Grants.gov)"
	@echo "  nsf-awards-download  Download NSF awarded grants into data/grants (via NSF Awards API)"
	@echo "  nsf-opps-download    Download NSF funding opportunities pages into data/grants (scrapes nsf.gov)"
	@echo "  nsf-from-csv         Build grant text files from CSV under data/grants/NSF_database*.csv"
	@echo "  grants-batch         Build next N (COUNT=20) grant profiles from data/grants/"
	@echo "  grants-refresh       One-shot: rebuild data/grants from CSV with filtering + section extraction"

rebuild-taxonomy:
	python -m mapping.build_taxonomy_embeddings --all --force

validate-taxonomy:
	python -m mapping.validate_taxonomy --all --strict

taxonomy-refresh: rebuild-taxonomy validate-taxonomy

synonyms-build:
	# 1) Generate safe format-level variants
	python -m mapping.build_synonyms --all --max 12
	# 2) Merge auto variants into curated files and delete autos to keep things tidy
	python -m mapping.merge_auto_synonyms --all --delete-auto

grants-all:
	python -m mapping.grant_profile_builder -all

orgs-all:
	python -m mapping.org_profile_builder -all

# Rank grants for a single org profile
recs:
	@if [ -z "$(ORG)" ]; then \
		echo "Usage: make recs ORG=$(ORGS_DIR)/<org>_profile.json [TOP=$(TOP)] [GRANTS_DIR=$(GRANTS_DIR)] [OUT=reports/<org>_recommendations.json]"; \
		exit 2; \
	fi; \
	mkdir -p reports; \
	OUTARG=""; if [ -n "$(OUT)" ]; then OUTARG="--out $(OUT)"; else \
	  b=$$(basename "$(ORG)"); base=$${b%_profile.json}; OUTARG="--out reports/$${base}_recommendations.json"; fi; \
	python -m matching.matching_engine --org "$(ORG)" --grants "$(GRANTS_DIR)" --top "$(TOP)" --explain $$OUTARG

# Rank grants for all org profiles under ORGS_DIR, write JSON to reports/
recs-all:
	@mkdir -p reports; \
	count=0; fail=0; \
	for f in $(ORGS_DIR)/*_profile.json; do \
	  [ -e "$$f" ] || continue; \
	  b=$$(basename "$$f"); base=$${b%_profile.json}; \
	  echo "[recs] $$b"; \
	  python -m matching.matching_engine --org "$$f" --grants "$(GRANTS_DIR)" --top "$(TOP)" --explain --out "reports/$${base}_recommendations.json" || fail=$$((fail+1)); \
	  count=$$((count+1)); \
	done; \
	echo "[done] generated $$count recommendation files in reports/ (fail=$$fail)"; \
	[ "$$fail" -eq 0 ]

# Download NSF opportunities into data/grants using Grants.gov API
# Optional env vars:
#   GRANTS_GOV_API_KEY   (recommended; falls back to UI endpoint if absent)
#   STATUSES             (e.g., "posted" or "posted|forecasted"; default posted)
#   SINCE                (YYYY-MM-DD; optional)
#   MAX                  (default 2000)
nsf-download:
	@echo "[nsf-download] Fetching NSF opportunities to data/grants"; \
	python -m extraction.fetch_nsf_grants --out-dir data/grants $${STATUSES:+--statuses "$$STATUSES"} $${SINCE:+--since "$$SINCE"} $${MAX:+--max "$$MAX"}

# Download NSF awarded grants into data/grants using the NSF Awards API
# Options via env:
#   SINCE  (YYYY-MM-DD)
#   UNTIL  (YYYY-MM-DD)
#   MAX    (default 2000)
nsf-awards-download:
	@echo "[nsf-awards-download] Fetching NSF awards to data/grants"; \
	python -m extraction.fetch_nsf_awards --out-dir data/grants $${SINCE:+--since "$$SINCE"} $${UNTIL:+--until "$$UNTIL"} $${MAX:+--max "$$MAX"}

# Scrape NSF funding opportunities listing and detail pages into data/grants
# Options via env:
#   MAX    (default 500)
# The scraper is lightweight and uses only stdlib; it honors a polite User-Agent.
nsf-opps-download:
	@echo "[nsf-opps-download] Fetching NSF funding opportunities into data/grants"; \
	python -m extraction.fetch_nsf_opportunities --out-dir data/grants $${MAX:+--max "$$MAX"}

# Build grant text files from a CSV (with optional URL fetching)
# Env:
#   CSV=data/grants/NSF_database.csv (or directory containing a CSV)
#   NO_FETCH=1 to disable URL fetch
#   OVERWRITE=1 to overwrite existing files

nsf-from-csv:
	@echo "[nsf-from-csv] Building grant files from CSV"; \
	python -m extraction.build_grants_from_csv $${CSV:+--csv "$$CSV"} --out-dir data/grants $${NO_FETCH:+--no-fetch} $${OVERWRITE:+--overwrite}

# Build next N grant profiles (skips those already processed)
# Env: COUNT=20 by default
grants-batch:
	@echo "[grants-batch] Building next $${COUNT:-20} grant profiles"; \
	python -m mapping.process_grants_batch --count "$${COUNT:-20}"

# One command to refresh grant text files from CSV with recommended flags
# Automatically detects CSV (defaults to data/NSF_database/nsf_funding.csv).
# Env overrides:
#   CSV=path/to.csv    Specify CSV path explicitly
#   OVERWRITE=1        Overwrite existing files (default on)
#   PRUNE=1            Delete .txt for filtered-out rows (default on)

grants-refresh:
	@echo "[grants-refresh] Rebuilding grant texts from CSV with filtering and selected sections"; \
	python -m extraction.refresh_grants $${CSV:+--csv "$$CSV"} $${OUT_DIR:+--out-dir "$$OUT_DIR"}

# End-to-end convenience: refresh taxonomies, rebuild grant texts, build next N profiles,
# process orgs, and generate recommendations for all org profiles.
# Env overrides:
#   COUNT=50           Number of grant profiles to build in batch (default 50)
#   CSV=...            CSV path for grant text refresh (optional; auto-detected if omitted)
#   OUT_DIR=...        Output dir for grant texts (optional)
e2e:
	@echo "[e2e] 1/5 taxonomy-refresh"; \
	$(MAKE) taxonomy-refresh && \
	echo "[e2e] 2/5 grants-refresh"; \
	$(MAKE) grants-refresh && \
	echo "[e2e] 3/5 grants-batch (COUNT=$${COUNT:-50})"; \
	COUNT=$${COUNT:-50} $(MAKE) grants-batch && \
	echo "[e2e] 4/5 orgs-all"; \
	$(MAKE) orgs-all && \
	echo "[e2e] 5/5 recs-all"; \
	$(MAKE) recs-all
