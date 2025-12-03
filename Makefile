.PHONY: rebuild-taxonomy validate-taxonomy taxonomy-refresh help grants-all orgs-all recs recs-all

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

rebuild-taxonomy:
	python -m pipeline.build_taxonomy_embeddings --all --force

validate-taxonomy:
	python -m pipeline.validate_taxonomy --all --strict

taxonomy-refresh: rebuild-taxonomy validate-taxonomy

grants-all:
	python -m pipeline.grant_profile_builder -all

orgs-all:
	python -m pipeline.org_profile_builder -all

# Rank grants for a single org profile
recs:
	@if [ -z "$(ORG)" ]; then \
		echo "Usage: make recs ORG=$(ORGS_DIR)/<org>_profile.json [TOP=$(TOP)] [GRANTS_DIR=$(GRANTS_DIR)] [OUT=reports/<org>_recommendations.json]"; \
		exit 2; \
	fi; \
	mkdir -p reports; \
	OUTARG=""; if [ -n "$(OUT)" ]; then OUTARG="--out $(OUT)"; else \
	  b=$$(basename "$(ORG)"); base=$${b%_profile.json}; OUTARG="--out reports/$${base}_recommendations.json"; fi; \
	python -m pipeline.matching_engine --org "$(ORG)" --grants "$(GRANTS_DIR)" --top "$(TOP)" --explain $$OUTARG

# Rank grants for all org profiles under ORGS_DIR, write JSON to reports/
recs-all:
	@mkdir -p reports; \
	count=0; fail=0; \
	for f in $(ORGS_DIR)/*_profile.json; do \
	  [ -e "$$f" ] || continue; \
	  b=$$(basename "$$f"); base=$${b%_profile.json}; \
	  echo "[recs] $$b"; \
	  python -m pipeline.matching_engine --org "$$f" --grants "$(GRANTS_DIR)" --top "$(TOP)" --explain --out "reports/$${base}_recommendations.json" || fail=$$((fail+1)); \
	  count=$$((count+1)); \
	done; \
	echo "[done] generated $$count recommendation files in reports/ (fail=$$fail)"; \
	[ "$$fail" -eq 0 ]
