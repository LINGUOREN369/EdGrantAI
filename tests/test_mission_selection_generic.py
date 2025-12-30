import json
import re
from pathlib import Path

from pipeline.canonical_mapper import map_all_taxonomies
from pipeline.section_utils import assign_sections_to_phrases


def _load_profile(name: str):
    p = Path(f"data/processed_grants/{name}_profile.json")
    assert p.exists(), f"Profile not found: {p}"
    data = json.loads(p.read_text(encoding="utf-8"))
    return data


def _title_from_text(txt: str):
    for ln in txt.splitlines():
        ln = ln.strip()
        if ln.lower().startswith("title:"):
            return ln.split(":", 1)[1].strip()
    return None


def test_sos_bio_mission_selection_prefers_domain_over_broad_generic():
    data = _load_profile("nsf_a_science_of_science_approach_to_analyzing_and_innovating_the_biomedical_research_enterprise_sos_bio")
    phrases = data.get("extracted_phrases") or []
    text = Path(data["source"]["path"]).read_text(encoding="utf-8")
    structured = data.get("extracted_phrases_structured") or assign_sections_to_phrases(phrases, text)
    title = _title_from_text(text)

    mapped = map_all_taxonomies(phrases, structured, doc_title=title, full_text=text)
    missions = [d.get("tag", "").lower() for d in mapped.get("mission_tags", [])]
    # Ensure that if 'broadening participation' appears anywhere, it is not the only mission
    assert not (len(missions) == 1 and any("broadening participation" in m for m in missions))


def test_ate_prefers_program_title_over_generic_pathways():
    data = _load_profile("nsf_advanced_technological_education_ate")
    phrases = data.get("extracted_phrases") or []
    text = Path(data["source"]["path"]).read_text(encoding="utf-8")
    structured = data.get("extracted_phrases_structured") or assign_sections_to_phrases(phrases, text)
    title = _title_from_text(text)

    mapped = map_all_taxonomies(phrases, structured, doc_title=title, full_text=text)
    missions = [d.get("tag", "").lower() for d in mapped.get("mission_tags", [])]
    # Prefer ATE/technician education over generic 'educational pathways'
    # Expect that a primary mission includes 'advanced technological education' or 'technician'
    assert any("advanced technological education" in m or "technician" in m for m in missions)
    # If 'educational pathways' is present, it should not be the only mission
    assert not (len(missions) == 1 and any("educational pathways" in m for m in missions))

