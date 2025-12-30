"""
Canonical taxonomy mapper.

Maps extracted phrases to canonical taxonomy tags using precomputed taxonomy
embeddings and semantic similarity.

Usage examples:
  - from pipeline.canonical_mapper import map_all_taxonomies
    tags = map_all_taxonomies(["robotics clubs", "middle school girls"])

Data locations:
  - Taxonomies: data/taxonomy/*.json
  - Embeddings: data/taxonomy/embeddings/*_embeddings.json

Environment:
  Requires OPENAI_API_KEY (phrase embeddings are computed at match time).
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import re
from .embedding_matcher import match_phrase_to_tag, load_taxonomy_embeddings, top_k_matches
from .config import settings


# -------------------------------------------------------------
# Helper: Load canonical taxonomy tag lists
# -------------------------------------------------------------
def load_taxonomy_list(name: str) -> List[str]:
    """
    Load a taxonomy JSON array such as:
    mission_tags.json, population_tags.json, etc.
    """
    path = settings.TAXONOMY_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {path}")
    with open(path, "r") as f:
        return json.load(f)


# -------------------------------------------------------------
# Helper: Load taxonomy embeddings (precomputed)
# -------------------------------------------------------------
def load_embeddings(name: str) -> Dict[str, List[float]]:
    """
    Load precomputed embeddings for a taxonomy list.
    Expects files like mission_tags_embeddings.json
    """
    path = settings.TAXONOMY_EMBEDDINGS_DIR / f"{name}_embeddings.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing embeddings for taxonomy '{name}'. Expected: {path}"
        )
    return load_taxonomy_embeddings(str(path))


# -------------------------------------------------------------
# Helper: Direct (non-embedding) mapping by normalized text
# -------------------------------------------------------------
def _normalize_text(s: str) -> str:
    """Normalize by lowercasing and removing all non-alphanumeric characters.
    This makes mapping insensitive to case, whitespace, and punctuation/hyphens.
    """
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _load_synonyms_map(taxonomy_name: str) -> Dict[str, str]:
    """Load synonyms maps for a taxonomy.
    - Scans data/taxonomy/synonyms/ for files starting with
      f"{taxonomy_name}_synonyms" and ending with .json
    - Merges all into a single dict of normalized synonym phrase -> canonical tag
    """
    syn_dir = settings.TAXONOMY_DIR / "synonyms"
    out: Dict[str, str] = {}
    if not syn_dir.exists() or not syn_dir.is_dir():
        return out
    # Load auto files first, then manual to allow manual overrides on conflicts
    files_all = list(syn_dir.glob(f"{taxonomy_name}_synonyms*.json"))
    # Ignore auto files by default; rely on curated/merged files
    files = [p for p in files_all if not p.name.endswith(".auto.json")]
    def _prio(p: Path) -> tuple:
        name = p.name.lower()
        # Keep deterministic order; plain name wins over .manual.json in tie
        return (0, name)
    for p in sorted(files, key=_prio):
        try:
            with open(p, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Case 1: flat map of synonym -> canonical
                    if all(isinstance(v, str) for v in data.values()):
                        for k, v in data.items():
                            if isinstance(k, str) and isinstance(v, str) and v:
                                out[_normalize_text(k)] = v
                    else:
                        # Case 2: grouped by canonical tag
                        for canonical, val in data.items():
                            syns = None
                            if isinstance(val, list):
                                syns = val
                            elif isinstance(val, dict) and isinstance(val.get("synonyms"), list):
                                syns = val.get("synonyms")
                            if syns:
                                for s in syns:
                                    if isinstance(s, str) and s:
                                        out[_normalize_text(s)] = canonical
                elif isinstance(data, list):
                    # Case 3: list of {canonical, synonyms: []}
                    for item in data:
                        if isinstance(item, dict) and isinstance(item.get("canonical"), str) and isinstance(item.get("synonyms"), list):
                            canonical = item["canonical"]
                            for s in item["synonyms"]:
                                if isinstance(s, str) and s:
                                    out[_normalize_text(s)] = canonical
        except Exception:
            # Skip malformed files but continue
            continue
    return out


# -------------------------------------------------------------
# Main: Map extracted phrases to canonical tags
# -------------------------------------------------------------
def _threshold_for_taxonomy(taxonomy_name: str) -> float:
    k = settings.THRESHOLD_KEY_BY_TAXONOMY.get(taxonomy_name, "default")
    return float(settings.THRESHOLDS.get(k, settings.THRESHOLDS.get("default", 0.51)))


def _loose_threshold_for_taxonomy(taxonomy_name: str) -> float:
    k = settings.THRESHOLD_KEY_BY_TAXONOMY.get(taxonomy_name, "default")
    return float(getattr(settings, "THRESHOLDS_LOOSE", {}).get(k, settings.THRESHOLDS.get(k, 0.5)))


def map_phrases_to_canonical(
    extracted_phrases: List[str],
    taxonomy_name: str,
    phrase_sections: Dict[str, str] | None = None,
    similarity_threshold: float | None = None,
    top_k: int | None = None,
) -> List[Dict]:
    """
    Map extracted phrases to canonical tags using semantic similarity.

    Returns a list of dictionaries:
    [
        {
            "tag": canonical_tag,
            "source_text": phrase,
            "confidence": score
        },
        ...
    ]
    """

    # Load embeddings for this taxonomy
    taxonomy_embeddings = load_embeddings(taxonomy_name)
    # Build direct map (normalized) for canonical tags and optional synonyms
    direct_map: Dict[str, str] = {}
    try:
        for tag in load_taxonomy_list(taxonomy_name):
            if isinstance(tag, str):
                direct_map[_normalize_text(tag)] = tag
    except Exception:
        # If tag list not found, keep direct_map empty
        pass
    # Merge synonyms (if present)
    syn_map = _load_synonyms_map(taxonomy_name)
    direct_map.update(syn_map)
    results = []

    # Resolve defaults from settings if not provided
    if similarity_threshold is None:
        similarity_threshold = _threshold_for_taxonomy(taxonomy_name)
    if top_k is None:
        top_k = settings.TOP_K_BY_TAXONOMY.get(taxonomy_name, settings.TOP_K)

    top1_gate = taxonomy_name in getattr(settings, "TOP1_TAXONOMIES", [])

    # Heuristic guardrails to reduce systemic misclassification
    audience_like = re.compile(r"\b(k[-–]?12|k-5|grades?\s*(?:k|\d+(?:-\d+)?)|elementary|middle\s+school|high\s+school|higher\s+education|undergraduate|graduate|postdoctoral|students?|teachers?|instructors?|learners?)\b", re.I)
    redflag_gate = re.compile(r"\b(only|limited|eligib|require|required|must|submission\s*limit|letter\s*of\s*intent|prepropos|IRB|human\s*subjects|data\s*management|mentoring|letters\s*of\s*collaboration)\b", re.I)
    # Mechanism acronyms and spelled-out variants that should not produce mission tags
    mech_acronyms = re.compile(r"\b(REU|RUI|GOALI|CAREER|EAGER|RAPID|RAISE|SBIR|STTR)\b", re.I)
    mech_spelled = re.compile(
        r"\b(Research Experiences for Undergraduates|Grant Opportunities for Academic Liaison with Industry|Facilitating Research at Primarily Undergraduate Institutions|Small Business Innovation Research|Small Business Technology Transfer)\b",
        re.I,
    )

    def _get_section(phrase: str) -> str:
        if not phrase_sections:
            return "Other"
        return phrase_sections.get((phrase or "").lower().strip(), "Other")

    def _allow_mapping(phrase: str, tag: str) -> bool:
        # Org type: avoid mapping audience phrases to organization types
        if taxonomy_name == "org_types":
            if audience_like.search(phrase or ""):
                return False
        # Red flags: require strong gating terms in the phrase
        if taxonomy_name == "red_flag_tags":
            if not redflag_gate.search(phrase or ""):
                return False
            if phrase_sections and _get_section(phrase) != "Eligibility Information":
                return False
        # Mission: tighten computing-specific tags unless explicit cues present
        if taxonomy_name == "mission_tags":
            # Never allow mechanism/instrument terms to create mission tags
            if mech_acronyms.search(phrase or "") or mech_spelled.search(phrase or ""):
                return False
            # Allow mission only from Introduction / Program Description when provenance present
            if phrase_sections and _get_section(phrase) not in {"Introduction", "Program Description"}:
                return False
            if tag.lower() in {"computing education research", "computer science education", "computing education"}:
                if not re.search(r"\b(comput|computer\s*science|\bCS\b|coding)\b", (phrase or ""), re.I):
                    return False
        # Population: avoid overgeneralizing English learners from multilingual
        if taxonomy_name == "population_tags":
            if tag.lower().strip() == "english learners":
                if not re.search(r"\benglish\b", (phrase or ""), re.I):
                    return False
        return True

    for phrase in extracted_phrases:
        # 1) Direct dictionary match (case/space/punctuation insensitive)
        norm = _normalize_text(phrase)
        direct_tag = direct_map.get(norm)
        if direct_tag and _allow_mapping(phrase, direct_tag):
            results.append(
                {
                    "tag": direct_tag,
                    "source_text": phrase,
                    "confidence": 1.0,
                }
            )
            # Skip embedding fallback for this phrase
            continue

        # 2) Embedding-based fallback with strict-then-loose thresholds
        candidates = top_k_matches(phrase, taxonomy_embeddings, k=top_k)

        def _append_by_thresh(thresh: float) -> int:
            appended = 0
            if top1_gate:
                if candidates:
                    tag, score = candidates[0]
                    if score >= thresh and _allow_mapping(phrase, tag):
                        results.append(
                            {
                                "tag": tag,
                                "source_text": phrase,
                                "confidence": round(score, 4),
                            }
                        )
                        appended += 1
                return appended
            # Not top-1 gate: collect all meeting threshold
            for tag, score in candidates:
                if score >= thresh and _allow_mapping(phrase, tag):
                    results.append(
                        {
                            "tag": tag,
                            "source_text": phrase,
                            "confidence": round(score, 4),
                        }
                    )
                    appended += 1
            return appended

        added = _append_by_thresh(float(similarity_threshold))
        if added == 0:
            loose = _loose_threshold_for_taxonomy(taxonomy_name)
            # Only attempt a looser pass if it is actually looser
            if float(loose) < float(similarity_threshold):
                _append_by_thresh(float(loose))

    # Deduplicate by tag across phrases: keep highest confidence; aggregate sources
    best_by_tag: Dict[str, Dict] = {}
    for item in results:
        tag = item["tag"]
        conf = float(item.get("confidence", 0.0))
        if tag not in best_by_tag:
            best_by_tag[tag] = {
                "tag": tag,
                "source_text": item.get("source_text"),
                "confidence": conf,
                "sources": [item.get("source_text")] if item.get("source_text") else [],
            }
        else:
            # Update best confidence and representative source
            if conf > best_by_tag[tag]["confidence"]:
                best_by_tag[tag]["confidence"] = conf
                best_by_tag[tag]["source_text"] = item.get("source_text")
            # Collect all sources
            src = item.get("source_text")
            if src and src not in best_by_tag[tag]["sources"]:
                best_by_tag[tag]["sources"].append(src)

    # Sort by confidence desc for stable output
    deduped = sorted(best_by_tag.values(), key=lambda d: d["confidence"], reverse=True)
    # Re-round confidence for presentation
    for d in deduped:
        d["confidence"] = round(float(d["confidence"]), 4)

    return deduped


# -------------------------------------------------------------
# Multi-taxonomy wrapper
# -------------------------------------------------------------
def map_all_taxonomies(
    extracted_phrases: List[str],
    phrases_structured: List[Dict] | None = None,
    *,
    doc_title: str | None = None,
    full_text: str | None = None,
) -> Dict[str, List[Dict]]:
    """
    Map phrases across all four taxonomy types.
    """
    out: Dict[str, List[Dict]] = {}
    # Derive phrase->section map when structured provided
    phrase_sections: Dict[str, str] | None = None
    if phrases_structured:
        phrase_sections = {}
        for item in phrases_structured:
            if isinstance(item, dict):
                t = (item.get("text") or "").lower().strip()
                sec = item.get("section") or "Other"
                if t and t not in phrase_sections:
                    phrase_sections[t] = sec

    for tax in settings.TAXONOMIES:
        key = settings.TAXONOMY_TO_OUTPUT_KEY.get(tax, tax)
        out[key] = map_phrases_to_canonical(extracted_phrases, tax, phrase_sections=phrase_sections)

    # Deterministic NSF mapping layer (post-processing)
    phrases = extracted_phrases or []

    def _append(dst_key: str, tag: str, phrase: str):
        lst = out.setdefault(dst_key, [])
        if not any(d.get("tag") == tag for d in lst):
            lst.append({"tag": tag, "source_text": phrase, "confidence": 1.0})

    # 1) Deterministic org type mapping
    for p in phrases:
        pl = (p or "").lower()
        if "institutions of higher education" in pl:
            _append("org_type_tags", "institution_of_higher_education", p)
        if ("non-profit, non-academic organizations" in pl) or ("nonprofit" in pl or "non-profit" in pl):
            _append("org_type_tags", "nonprofit", p)

    # 2) Deterministic red-flag mapping: submission limits
    re_one = re.compile(r"\bone\s+proposal\b|\blimited\s+submission\b", re.I)
    for p in phrases:
        pl = (p or "").lower()
        if (
            "limit on number of proposals" in pl
            or "submission limit" in pl
            or re_one.search(pl)
        ):
            _append("red_flag_tags", "submission_limit", p)

    # 3) Mission tag cleanup: remove mechanism-driven mission tags
    mech_phrase_re = re.compile(
        r"\b(REU|RUI|GOALI|CAREER|EAGER|RAPID|RAISE|SBIR|STTR)\b|\b(Research Experiences for Undergraduates|Grant Opportunities for Academic Liaison with Industry|Facilitating Research at Primarily Undergraduate Institutions)\b",
        re.I,
    )
    missions = out.get("mission_tags", []) or []
    missions_filtered = [m for m in missions if not mech_phrase_re.search(str(m.get("source_text") or ""))]
    out["mission_tags"] = missions_filtered

    # 4) Generic mission-tag selection using provenance, title, and repetition
    def _mission_selection():
        structured = phrases_structured or []
        allowed_secs = {"Introduction", "Program Description"}
        stoplist = set(getattr(settings, "MISSION_GENERIC_STOPLIST", []))
        title_low = (doc_title or "").lower()
        text_low = (full_text or "").lower()

        # Build phrase -> (section, count, in_title)
        cand = []
        for item in structured:
            if not isinstance(item, dict):
                continue
            phrase = (item.get("text") or "").strip()
            sec = item.get("section") or "Other"
            if not phrase or sec not in allowed_secs:
                continue
            pl = phrase.lower()
            in_title = bool(title_low) and (pl in title_low)
            # Count occurrences in full text; if missing, default to 1
            if text_low:
                count = len(re.findall(re.escape(pl), text_low, re.I))
            else:
                count = 1
            score = 0
            if in_title:
                score += 3
            if sec == "Program Description":
                score += 2
            elif sec == "Introduction":
                score += 1
            if count >= 2:
                score += 2
            if pl in stoplist:
                score -= 2
            cand.append({"phrase": phrase, "section": sec, "in_title": in_title, "count": count, "score": score, "is_stop": pl in stoplist})

        if not cand:
            return

        # Rank by score desc then phrase length desc (favor specific), then alpha
        cand.sort(key=lambda x: (x["score"], len(x["phrase"])), reverse=True)

        # Build mapping from phrase -> mapped mission tag items (if any)
        mapped_items = out.get("mission_tags", []) or []
        phrase_to_items: Dict[str, List[Dict]] = {}
        for it in mapped_items:
            srcs = it.get("sources") or [it.get("source_text")]
            for s in (srcs or []):
                if s:
                    phrase_to_items.setdefault(s, []).append(it)

        primary: List[Dict] = []
        secondary: List[Dict] = []

        def _make_item(ph: str, allow_from_existing: bool = True) -> Dict:
            # Prefer existing mapped item
            if allow_from_existing:
                items = phrase_to_items.get(ph)
                if items:
                    # take first
                    return {k: items[0].get(k) for k in ("tag", "source_text", "confidence")}
            # fallback: use phrase as tag
            return {"tag": ph, "source_text": ph, "confidence": 0.9}

        # Select top 1-2 primary; demote stoplist unless title two-times-in-PD condition holds
        for c in cand:
            if len(primary) >= 2:
                break
            if c["is_stop"] and not (c["in_title"] or (c["section"] == "Program Description" and c["count"] >= 2)):
                secondary.append(_make_item(c["phrase"]))
                continue
            primary.append(_make_item(c["phrase"]))

        if primary:
            out["mission_tags"] = primary
        # Add secondary list when present
        if secondary:
            # de-duplicate by tag
            seen = set()
            sec_clean = []
            for it in secondary:
                t = it.get("tag")
                if t and t not in seen:
                    sec_clean.append(it)
                    seen.add(t)
            out["secondary_mission_tags"] = sec_clean

    _mission_selection()

    return out
