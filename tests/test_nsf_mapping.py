import json
from pathlib import Path

from pipeline.canonical_mapper import map_all_taxonomies


def _load_example_phrases() -> list[str]:
    example = Path("data/processed_grants/nsf_chemical_measurement_and_imaging_cmi_profile.json")
    assert example.exists(), f"Example profile not found: {example}"
    data = json.loads(example.read_text(encoding="utf-8"))
    phrases = data.get("extracted_phrases") or []
    assert isinstance(phrases, list)
    return phrases


def _tags(mapped: dict, key: str) -> set[str]:
    return {d.get("tag") for d in mapped.get(key, []) if isinstance(d, dict)}


def test_deterministic_org_type_mapping():
    phrases = _load_example_phrases()
    mapped = map_all_taxonomies(phrases)
    org_types = _tags(mapped, "org_type_tags")
    assert org_types, "org_type_tags should not be empty"
    assert "institution_of_higher_education" in org_types
    assert "nonprofit" in org_types


def test_submission_limit_redflag():
    phrases = _load_example_phrases()
    mapped = map_all_taxonomies(phrases)
    reds = _tags(mapped, "red_flag_tags")
    assert "submission_limit" in reds


def test_mission_not_from_reu():
    phrases = _load_example_phrases()
    mapped = map_all_taxonomies(phrases)
    missions = _tags(mapped, "mission_tags")
    assert "undergraduate research experiences" not in missions

