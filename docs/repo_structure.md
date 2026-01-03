# Repository Structure

Tree overview (large data directories are summarized):

EdGrantAI/
|-- README.md
|-- LICENSE
|-- Makefile
|-- requirements.txt
|-- environment.yml
|-- cli/
|   |-- __init__.py
|   \-- interactive.py
|-- common/
|   |-- __init__.py
|   \-- config.py
|-- extraction/
|   |-- __init__.py
|   |-- build_grants_from_csv.py
|   |-- cke.py
|   |-- deadline_extractor.py
|   |-- fetch_nsf_awards.py
|   |-- fetch_nsf_grants.py
|   |-- fetch_nsf_opportunities.py
|   |-- funding_extractor.py
|   |-- refresh_grants.py
|   \-- section_utils.py
|-- mapping/
|   |-- __init__.py
|   |-- build_synonyms.py
|   |-- build_taxonomy_embeddings.py
|   |-- canonical_mapper.py
|   |-- embedding_matcher.py
|   |-- grant_profile_builder.py
|   |-- merge_auto_synonyms.py
|   |-- org_profile_builder.py
|   |-- process_grants_batch.py
|   \-- validate_taxonomy.py
|-- matching/
|   |-- __init__.py
|   |-- explain_reports.py
|   \-- matching_engine.py
|-- prompts/
|   |-- cke_prompt_nsf_v1.txt
|   \-- matching_explainer_prompt_v1.txt
|-- data/
|   |-- grants/ (many .txt files)
|   |-- NSF_database/ (CSV inputs)
|   |-- orgs/ (many .txt files)
|   |-- processed_grants/ (many *_profile.json files)
|   |-- processed_orgs/ (many *_profile.json files)
|   \-- taxonomy/
|       |-- embeddings/
|       |   |-- geography_tags_embeddings.json
|       |   |-- mission_tags_embeddings.json
|       |   |-- org_types_embeddings.json
|       |   |-- population_tags_embeddings.json
|       |   \-- red_flag_tags_embeddings.json
|       |-- synonyms/
|       |   |-- geography_tags_synonyms.json
|       |   |-- mission_tags_synonyms.json
|       |   |-- nsf_programs_synonyms.json
|       |   |-- org_types_synonyms.json
|       |   |-- population_tags_synonyms.json
|       |   |-- red_flag_tags_synonyms.json
|       |   \-- README.synonyms.md
|       |-- changelog.md
|       |-- geography_tags.json
|       |-- mission_tags.json
|       |-- nsf_programs.json
|       |-- org_types.json
|       |-- population_tags.json
|       |-- red_flag_tags.json
|       \-- schema_version.json
|-- docs/
|   |-- architecture_design.md
|   |-- data_source_and_handling.md
|   |-- extraction.md
|   |-- profile_building.md
|   |-- matching_algorithm_and_formula.md
|   |-- makefile_commands.md
|   |-- EdGrantAI_Case_Study.md
|   |-- cover.svg
|   |-- structure.png
|   \-- workflow.png
|-- reports/ (generated outputs)
\-- tests/
    |-- test_mission_selection_generic.py
    |-- test_nsf_mapping.py
    \-- test_section_provenance.py
