.PHONY: rebuild-taxonomy validate-taxonomy taxonomy-refresh help

help:
	@echo "Available targets:"
	@echo "  rebuild-taxonomy     Rebuild embeddings for all taxonomies (force)"
	@echo "  validate-taxonomy    Validate taxonomy lists vs. embeddings (strict)"
	@echo "  taxonomy-refresh     Rebuild then validate (reliable one-liner)"
	@echo "  grants-all           Process all grant text files in data/grants"

rebuild-taxonomy:
	python -m pipeline.build_taxonomy_embeddings --all --force

validate-taxonomy:
	python -m pipeline.validate_taxonomy --all --strict

taxonomy-refresh: rebuild-taxonomy validate-taxonomy

grants-all:
	python -m pipeline.grant_profile_builder -all
