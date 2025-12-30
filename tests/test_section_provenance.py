import json
import re
from pathlib import Path

from pipeline.canonical_mapper import map_all_taxonomies
from pipeline.section_utils import assign_sections_to_phrases


def load_example_profile():
    p = Path("data/processed_grants/nsf_chemical_measurement_and_imaging_cmi_profile.json")
    assert p.exists(), "Example processed grant not found; build it first."
    return json.loads(p.read_text(encoding="utf-8"))


def test_structured_phrases_and_sections():
    data = load_example_profile()
    phrases = data.get("extracted_phrases") or []
    text = Path(data["source"]["path"]).read_text(encoding="utf-8")

    # Build structured provenance if not present in profile
    structured = data.get("extracted_phrases_structured")
    if not structured:
        structured = assign_sections_to_phrases(phrases, text)

    # Check eligibility examples
    sec_map = {d["text"]: d["section"] for d in structured if isinstance(d, dict)}
    assert sec_map.get("Institutions of Higher Education") in {"Eligibility Information", "Other"}
    # phrase may vary slightly; use regex find
    elig_phrase = None
    for k in sec_map:
        if re.search(r"limit on number of proposals", k, re.I):
            elig_phrase = k
            break
    assert elig_phrase is not None
    assert sec_map.get(elig_phrase) in {"Eligibility Information", "Other"}


def test_mapping_with_provenance():
    data = load_example_profile()
    phrases = data.get("extracted_phrases") or []
    # Construct structured with key eligibility phrases labeled explicitly
    structured = []
    for p in phrases:
        sec = "Other"
        low = (p or "").lower()
        if "institutions of higher education" in low:
            sec = "Eligibility Information"
        if "non-profit" in low or "nonprofit" in low or "non-academic organizations" in low:
            sec = "Eligibility Information"
        if "limit on number of proposals" in low:
            sec = "Eligibility Information"
        structured.append({"text": p, "section": sec})

    mapped = map_all_taxonomies(phrases, structured)

    org_types = {d.get("tag") for d in mapped.get("org_type_tags", [])}
    assert "institution_of_higher_education" in org_types
    assert "nonprofit" in org_types

    red_flags = {d.get("tag") for d in mapped.get("red_flag_tags", [])}
    assert "submission_limit" in red_flags

    missions = {d.get("tag") for d in mapped.get("mission_tags", [])}
    assert "undergraduate research experiences" not in missions

