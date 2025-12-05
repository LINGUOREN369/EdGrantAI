"""
Organization profile builder.

Runs the end-to-end pipeline on organization text:
  1) Controlled Keyphrase Extraction (CKE)
  2) Canonical mapping across taxonomies
  3) Attach taxonomy version and metadata
  4) Save profile (optional)

Python usage:
  - from pipeline.org_profile_builder import process_org
    path = process_org("org_0001", "Organization mission text here.")

CLI:
  - Build taxonomy embeddings first (once):
      - python -m pipeline.build_taxonomy_embeddings --all
  - Build a profile from a text file:
      - Derive id from filename:
          - python -m pipeline.org_profile_builder data/orgs/org_0001.txt
      - Specify id and output directory:
          - python -m pipeline.org_profile_builder data/orgs/org_0001.txt --org-id org_0001 --out-dir data/processed_orgs
      - Optionally include a source URL:
          - python -m pipeline.org_profile_builder data/orgs/org_0001.txt --source-url https://example.org/about
      - Convenience: if the first non-empty line of the text file is an http(s) URL, it is used as the source URL and omitted from the processed text.
  - Process all .txt org files in a directory (default: data/orgs):
      - python -m pipeline.org_profile_builder --all
      - Custom directory/extension/output:
          - python -m pipeline.org_profile_builder --all --dir data/orgs --ext .txt --out-dir data/processed_orgs
  - Output:
      - data/processed_orgs/org_0001_profile.json (includes source.path and optional source.url)

Environment:
  Requires OPENAI_API_KEY and taxonomy assets in data/taxonomy/.
"""

from __future__ import annotations

import argparse
import json
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from zoneinfo import ZoneInfo

from .cke import run_cke
from .canonical_mapper import map_all_taxonomies
from .config import settings


OUTPUT_DIR = settings.PROCESSED_ORGS_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCHEMA_VERSION_PATH = settings.SCHEMA_VERSION_PATH


def load_taxonomy_version() -> str:
    if SCHEMA_VERSION_PATH.exists():
        with open(SCHEMA_VERSION_PATH, "r") as f:
            data = json.load(f)
            return data.get("taxonomy_version", "0.0.0")
    return "0.0.0"


def build_org_profile(
    org_id: str,
    org_text: str,
    *,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Dict:
    """
    Full pipeline for organization text.
    1. Extract keyphrases via CKE
    2. Map phrases to canonical tags
    3. Attach taxonomy version & metadata
    4. Produce final org profile
    """

    extracted_phrases = run_cke(org_text)
    mapped_tags = map_all_taxonomies(extracted_phrases)

    # Post-processing guardrails & enrichments for org profiles
    # 1) Remove org_type tags derived from audience-like phrases (safety net)
    audience_like = re.compile(r"\b(k[-–]?12|k-5|grades?\s*(?:k|\d+(?:-\d+)?)|elementary|middle\s+school|high\s+school|higher\s+education|undergraduate|graduate|postdoctoral|students?|teachers?|instructors?|learners?)\b", re.I)
    otags = mapped_tags.get("org_type_tags", []) or []
    cleaned_otags = []
    for item in otags:
        sources = item.get("sources") or [item.get("source_text")]
        # Keep if any source is not audience-like
        keep = False
        for s in (sources or []):
            if s and not audience_like.search(s):
                keep = True
                break
        if keep or not sources:
            cleaned_otags.append(item)
    mapped_tags["org_type_tags"] = cleaned_otags

    # 2) Population enrichment for K-12 breadth and higher-ed instructors
    pops = mapped_tags.get("population_tags", []) or []
    pop_tags = {p.get("tag") for p in pops if isinstance(p, dict)}

    def _append_pop(tag: str, src: str):
        if tag not in pop_tags:
            pops.append({"tag": tag, "source_text": src, "confidence": 0.95})
            pop_tags.add(tag)

    if re.search(r"\bk[-–]?12\b", org_text, re.I):
        _append_pop("K-12 students", "derived: K-12 mention in org text")
        if "K-12 teachers" in pop_tags:
            _append_pop("middle school teachers", "derived: K-12 teachers breadth")
            _append_pop("high school teachers", "derived: K-12 teachers breadth")
    if re.search(r"\b(higher\s+education|postsecondary|college)\b", org_text, re.I):
        _append_pop("college instructors", "derived: higher education mention")
    mapped_tags["population_tags"] = pops

    # 3) Geography extraction from org text (lightweight)
    geos = mapped_tags.get("geography_tags", []) or []
    geo_tags = {g.get("tag") for g in geos if isinstance(g, dict)}

    def _append_geo(tag: str, src: str):
        if tag not in geo_tags:
            geos.append({"tag": tag, "source_text": src, "confidence": 0.99})
            geo_tags.add(tag)

    text_lower = org_text.lower()
    # Coarse geography only; require explicit U.S. tokens; do not infer from 'nationwide'/'national'
    if re.search(r"\b(united\s+states|u\.s\.|usa|u\.s\.a\.)\b", text_lower):
        _append_geo("United States", "derived: geography mention in org text")
    if re.search(r"\b(global|worldwide|international)\b", text_lower):
        _append_geo("global", "derived: geography mention in org text")
    # If org name/text contains a U.S. state name, tag single state
    _US_STATES = [
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
        "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana",
        "iowa", "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts",
        "michigan", "minnesota", "mississippi", "missouri", "montana", "nebraska",
        "nevada", "new hampshire", "new jersey", "new mexico", "new york", "north carolina",
        "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
        "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont",
        "virginia", "washington", "west virginia", "wisconsin", "wyoming", "district of columbia"
    ]
    for st in _US_STATES:
        if re.search(rf"\b{re.escape(st)}\b", text_lower):
            _append_geo("single state", f"derived: state name '{st.title()}' in org text")
            break
    mapped_tags["geography_tags"] = geos

    # 4) Org-type enforcement based on self-description
    otags2 = mapped_tags.get("org_type_tags", []) or []
    otag_set = {o.get("tag") for o in otags2 if isinstance(o, dict)}

    def _append_org_type(tag: str, src: str, conf: float = 0.99):
        if tag not in otag_set:
            otags2.append({"tag": tag, "source_text": src, "confidence": conf})
            otag_set.add(tag)

    if re.search(r"\bnon\s*profit|nonprofit\b", text_lower):
        # Force nonprofit classification when mentioned
        _append_org_type("501(c)(3) nonprofit", "derived: nonprofit mention in org text")

    if re.search(r"\b(edtech|education\s+technology|learning\s+platform|digital\s+learning\s+platform|ai[-\s]*powered\s+tutor|ai\s+tutoring|ai\s+tutor)\b", text_lower):
        _append_org_type("education technology organization", "derived: platform/edtech/AI tutoring mention")
    mapped_tags["org_type_tags"] = otags2

    # 5) Red-flag filtering: require multiple mentions in org text and high confidence
    rfs = mapped_tags.get("red_flag_tags", []) or []
    min_occ = getattr(settings, "RED_FLAG_MIN_OCCURRENCES_ORG", 2)
    rf_threshold = float(settings.THRESHOLDS.get("red_flags", 0.8))

    def _occurrences(text: str, phrase: str) -> int:
        if not phrase:
            return 0
        pat = re.compile(r"(?i)\b" + re.escape(phrase) + r"\b")
        return len(pat.findall(text))

    filtered_rfs = []
    for item in rfs:
        sources = item.get("sources") or [item.get("source_text")]
        total = 0
        for s in (sources or []):
            total += _occurrences(org_text, s or "")
        conf = float(item.get("confidence", 0.0))
        if total >= min_occ and conf >= rf_threshold:
            filtered_rfs.append(item)
    mapped_tags["red_flag_tags"] = filtered_rfs

    # 6) Mission tag filters & policy/grade-band rules (org-specific tightening)
    missions = mapped_tags.get("mission_tags", []) or []
    mission_filtered = []
    restricted_mission = {
        "after-school STEM programs",
        "out-of-school STEM programs",
        "informal STEM learning",
        "STEM career pathways",
    }
    # Signals that must appear in text for restricted tags
    sig_after_out = re.compile(r"\b(after\s*-?\s*school|afterschool|out\s*-?\s*of\s*-?\s*school|\bOST\b)\b", re.I)
    sig_informal = re.compile(r"\b(informal|museum|library|science\s+center|science\s+museum|maker|makerspace|community\s*-?\s*based)\b", re.I)
    sig_career = re.compile(r"\b(career\s+pathway|career\s+pathways|career\s+exploration|workforce|apprenticeship|internship|cte)\b", re.I)
    sig_policy = re.compile(r"\b(policy|advocacy|legislat|statewide\s+policy|policymak)\b", re.I)

    # Grade-band suppression helpers
    has_k12 = bool(re.search(r"\bk\s*[-–]?\s*12\b", org_text, re.I))
    grade_terms = re.compile(r"\b(elementary|middle\s+school|high\s+school|grades?\s*(?:k|\d+(?:-\d+)?))\b", re.I)
    has_specific_grades = bool(grade_terms.search(org_text))

    for item in missions:
        tag = (item.get("tag") or "").strip()
        conf = float(item.get("confidence", 0.0))
        keep = True
        # Restrict specific mission categories to explicit signals and conf >= 0.75
        if tag in restricted_mission:
            if tag == "informal STEM learning":
                keep = conf >= 0.75 and (sig_informal.search(org_text) or sig_after_out.search(org_text))
            elif tag == "STEM career pathways":
                keep = conf >= 0.75 and bool(sig_career.search(org_text))
            else:
                # after-school / out-of-school
                keep = conf >= 0.75 and bool(sig_after_out.search(org_text))

        # Policy requirement
        if keep and tag == "STEM education policy":
            keep = bool(sig_policy.search(org_text))

        # Grade-band suppression: if only generic K–12 is mentioned, allow only K-12 STEM education
        if keep and has_k12 and not has_specific_grades:
            if tag in {"elementary STEM education", "middle school STEM education", "high school STEM education"}:
                keep = False

        if keep:
            mission_filtered.append(item)
    mapped_tags["mission_tags"] = mission_filtered

    # 7) Population rules: require explicit textual support for select tags; remove school districts as a population
    pops2 = []
    for item in mapped_tags.get("population_tags", []) or []:
        tag = (item.get("tag") or "").strip().lower()
        keep = True
        if tag in {"rural students", "underserved communities", "low-income students"}:
            pattern = None
            if tag == "rural students":
                pattern = re.compile(r"\brural\b", re.I)
            elif tag == "underserved communities":
                pattern = re.compile(r"under\s*-?\s*served", re.I)
            elif tag == "low-income students":
                pattern = re.compile(r"low\s*-?\s*income|title\s*[i1]", re.I)
            keep = bool(pattern and pattern.search(org_text))
        if tag == "school districts":
            keep = False
        if keep:
            pops2.append(item)
    mapped_tags["population_tags"] = pops2

    # 8) Threshold enforcement (org-specific minimums)
    def _enforce_threshold(items: list, min_conf: float) -> list:
        out = []
        for it in items or []:
            if float(it.get("confidence", 0.0)) >= min_conf:
                out.append(it)
        return out

    mapped_tags["mission_tags"] = _enforce_threshold(mapped_tags.get("mission_tags"), 0.70)
    mapped_tags["population_tags"] = _enforce_threshold(mapped_tags.get("population_tags"), 0.65)
    mapped_tags["org_type_tags"] = _enforce_threshold(mapped_tags.get("org_type_tags"), 0.75)
    # Geography: keep explicit mentions regardless; otherwise enforce 0.85
    g2 = []
    for it in mapped_tags.get("geography_tags", []) or []:
        src = (it.get("source_text") or "") + " " + " ".join(it.get("sources") or [])
        explicit = bool(re.search(r"\b(united\s+states|u\.s\.|usa|u\.s\.a\.|global|worldwide|international|state name|derived: geography mention|derived: state name)\b", src, re.I))
        if explicit or float(it.get("confidence", 0.0)) >= 0.85:
            g2.append(it)
    mapped_tags["geography_tags"] = g2
    version = load_taxonomy_version()

    profile = {
        "org_id": org_id,
        "created_at": datetime.now(ZoneInfo(settings.TIMEZONE)).isoformat(),
        "taxonomy_version": version,
        "extracted_phrases": extracted_phrases,
        "canonical_tags": mapped_tags,
        "validation": {
            "rules_version": "0.0.10+",
            "notes": [
                "Dictionary-first; geography explicit or derived from state name",
                "Restricted mission tags require explicit signals",
                "Grade-band suppression if only generic K–12",
                "Policy tag requires policy/advocacy signals",
                "Population tags require explicit cues; no 'school districts' population",
                "Org-specific thresholds applied"
            ],
        },
        "source": {
            "path": str(source_path) if source_path else None,
            "url": str(source_url) if source_url else None,
        },
    }
    return profile


def save_org_profile(profile: Dict) -> Path:
    org_id = profile.get("org_id", "unknown_org")
    output_path = OUTPUT_DIR / f"{org_id}_profile.json"
    with open(output_path, "w") as f:
        json.dump(profile, f, indent=2)
    return output_path


def process_org(
    org_id: str,
    org_text: str,
    *,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Path:
    profile = build_org_profile(org_id, org_text, source_path=source_path, source_url=source_url)
    return save_org_profile(profile)


def _main(argv=None) -> int:
    global OUTPUT_DIR
    parser = argparse.ArgumentParser(description="Build an organization profile JSON from a plain text file.")
    parser.add_argument("input", nargs="?", help="Path to an org text file (e.g., data/orgs/org_0001.txt)")
    parser.add_argument("-o", "--org-id", help="ID for output filename; defaults to input filename stem.")
    parser.add_argument("--out-dir", help=f"Output directory (default: {OUTPUT_DIR})")
    parser.add_argument("--source-url", help="Optional source URL (stored in profile metadata).")
    parser.add_argument("-all", "-a", "--all", action="store_true", help="Process all text files in --dir (default: data/orgs).")
    parser.add_argument("--dir", default=str((settings.REPO_ROOT / "data" / "orgs").resolve()), help="Directory when using --all.")
    parser.add_argument("--ext", default=".txt", help="File extension to include when using --all (default: .txt).")

    args = parser.parse_args(argv)

    if args.all:
        dir_path = Path(args.dir)
        if not dir_path.exists() or not dir_path.is_dir():
            print(f"[error] Directory not found: {dir_path}")
            return 1
        files = sorted(p for p in dir_path.glob(f"*{args.ext}") if p.is_file())
        if not files:
            print(f"[warn] No files found in {dir_path} matching *{args.ext}")
            return 0
        if args.out_dir:
            OUTPUT_DIR = Path(args.out_dir)
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        ok = 0
        fail = 0
        t_start = time.time()
        for f in files:
            try:
                oid = args.org_id or f.stem
                text = f.read_text(encoding="utf-8")
                s_url = args.source_url
                # First non-empty line URL convenience
                if not s_url:
                    lines = text.splitlines()
                    for idx, raw in enumerate(lines):
                        line = raw.strip()
                        if not line:
                            continue
                        if line.startswith("http://") or line.startswith("https://"):
                            s_url = line
                            del lines[idx]
                            text = "\n".join(lines).lstrip("\n")
                        break
                t0 = time.time()
                out = process_org(oid, text, source_path=str(f), source_url=s_url)
                dt = time.time() - t0
                print(f"[ok] {f.name} → {out.name} ({dt:.2f}s)")
                ok += 1
            except Exception as e:
                print(f"[error] {f.name}: {e}")
                fail += 1
        total = time.time() - t_start
        print(f"[done] processed: {ok} ok, {fail} failed in {total:.2f}s")
        return 0 if fail == 0 else 1

    # Single-file mode
    if not args.input:
        parser.print_usage()
        return 2
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[error] Input file not found: {in_path}")
        return 1
    org_id = args.org_id or in_path.stem
    org_text = in_path.read_text(encoding="utf-8")
    source_url = args.source_url
    if not source_url:
        lines = org_text.splitlines()
        for idx, raw in enumerate(lines):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("http://") or line.startswith("https://"):
                source_url = line
                del lines[idx]
                org_text = "\n".join(lines).lstrip("\n")
            break
    if args.out_dir:
        OUTPUT_DIR = Path(args.out_dir)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        t0 = time.time()
        out = process_org(org_id, org_text, source_path=str(in_path), source_url=source_url)
        dt = time.time() - t0
        print(f"[ok] Saved profile → {out}  ({dt:.2f}s)")
        return 0
    except Exception as e:
        print(f"[error] Failed to build org profile: {e}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
