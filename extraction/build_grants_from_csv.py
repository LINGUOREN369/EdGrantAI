"""
Build grant text files from a CSV under data/grants.

Reads a CSV (or a directory containing one CSV) and creates one .txt per row,
optionally fetching solicitation pages and extracting key sections.
"""

from __future__ import annotations

import argparse
import csv
import html as ihtml
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from common.config import settings
from extraction.deadline_extractor import extract_deadline_info

try:  # type: ignore
    import requests  # noqa: F401
    HAVE_REQUESTS = True
except Exception:
    HAVE_REQUESTS = False

try:  # type: ignore
    from bs4 import BeautifulSoup  # noqa: F401
    HAVE_BS4 = True
except Exception:
    HAVE_BS4 = False


DEFAULT_OUT_DIR = (settings.REPO_ROOT / "data" / "grants").resolve()


def slugify(s: str, max_len: int = 100) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "opportunity"
    if len(s) > max_len:
        s = s[:max_len].rstrip("_")
    return s


def _best_column(row_keys: Sequence[str], candidates: Sequence[str]) -> Optional[str]:
    lower_map = {k.lower().strip(): k for k in row_keys}
    for c in candidates:
        if c in lower_map:
            return lower_map[c]
    return None


def _resolve_csv_path(path_like: Optional[str]) -> Path:
    if path_like:
        p = Path(path_like)
        if p.is_file():
            return p
        if p.is_dir():
            picks = sorted(p.glob("*.csv"))
            if not picks:
                raise FileNotFoundError(f"No CSV files found in directory: {p}")
            return picks[0]
        raise FileNotFoundError(f"CSV path not found: {p}")
    base_grants = settings.REPO_ROOT / "data" / "grants"
    base_db = settings.REPO_ROOT / "data" / "NSF_database"
    candidates = [
        base_db / "nsf_funding.csv",
        base_grants / "nsf_funding.csv",
        base_grants / "NSF_database.csv",
        base_grants / "NSF_database" / "NSF_database.csv",
    ]
    for c in candidates:
        if c.exists():
            return c
    for base in (base_db, base_grants):
        csvs = sorted(base.glob("*.csv"))
        if len(csvs) == 1:
            return csvs[0]
        if len(csvs) > 1:
            pref = [p for p in csvs if "fund" in p.name.lower() or "nsf" in p.name.lower()]
            if len(pref) == 1:
                return pref[0]
    if len(csvs) == 1:
        return csvs[0]
    raise FileNotFoundError(
        "CSV not found. Provide --csv <path> or place nsf_funding.csv under data/NSF_database/."
    )


def http_get(url: str, *, timeout: int = 30) -> Tuple[int, bytes]:
    headers = {
        "User-Agent": "EdGrantAI/1.0 (+https://github.com/)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close",
    }
    if HAVE_REQUESTS:
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            return r.status_code, r.content or b""
        except Exception:
            return 0, b""
    else:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.getcode(), resp.read()
        except urllib.error.HTTPError as e:
            try:
                data = e.read()
            except Exception:
                data = b""
            return e.code, data
        except Exception:
            return 0, b""


def extract_text_from_html(html: str) -> Tuple[Optional[str], str]:
    if HAVE_BS4:
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")
        for t in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            t.decompose()
        title = None
        if soup.title and soup.title.string:
            title = re.sub(r"\s+", " ", soup.title.string.strip())
        if not title:
            h1 = soup.select_one("h1")
            if h1:
                title = re.sub(r"\s+", " ", h1.get_text(" ", strip=True))
        containers = soup.select("main, article")
        if not containers:
            containers = soup.select('[role="main"], .nsf-rich-text, .rich-text, .content, #content, #content-area')
        if not containers:
            containers = [soup]
        parts: List[str] = []
        for root in containers:
            for el in root.select("h2, h3, h4, p, li"):
                txt = el.get_text(" ", strip=True)
                if txt:
                    parts.append(txt)
            if parts:
                break
        if not parts:
            txt = soup.get_text(" ", strip=True)
            parts = [txt] if txt else []
        body = "\n\n".join([re.sub(r"\s+", " ", p).strip() for p in parts if p.strip()])
        return title, body

    title = None
    m = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
    if m:
        title = ihtml.unescape(re.sub(r"\s+", " ", m.group(1)).strip())
    body = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    body = re.sub(r"<style[\s\S]*?</style>", " ", body, flags=re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    return title, body


def _select_sections(text: str) -> Tuple[str, List[str]]:
    """Return (selected_text, found_labels) for key NSF sections."""
    lines = text.splitlines()
    want_patterns = [
        ("Summary of Program Requirements", re.compile(r"^\s*(summary\s+of\s+program\s+requirements|synopsis\s+of\s+program|synopsis)\b.*$", re.I)),
        ("I. Introduction", re.compile(r"^\s*(i\.[\s\-]*)?introduction\b.*$", re.I)),
        ("II. Program Description", re.compile(r"^\s*(ii\.[\s\-]*)?program\s+description\b.*$", re.I)),
        ("III. Award Information", re.compile(r"^\s*(iii\.[\s\-]*)?award\s+information\b.*$", re.I)),
        ("IV. Eligibility Information", re.compile(r"^\s*(iv\.[\s\-]*)?eligibility\s+information\b.*$", re.I)),
    ]
    roman_boundary = re.compile(r"^\s*[IVXLCDM]+\.[^\S\n]*.*$", re.I)
    starts: List[Tuple[str, int]] = []
    for idx, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        for label, pat in want_patterns:
            if pat.match(line):
                starts.append((label, idx))
                break
    if not starts:
        return "", []
    starts.sort(key=lambda t: t[1])
    first_pos: Dict[str, int] = {}
    for label, pos in starts:
        if label not in first_pos:
            first_pos[label] = pos
    order = [
        "Summary of Program Requirements",
        "I. Introduction",
        "II. Program Description",
        "III. Award Information",
        "IV. Eligibility Information",
    ]
    if "Summary of Program Requirements" not in first_pos and any(lbl.startswith("Synopsis of Program") for lbl, _ in starts):
        first_pos["Summary of Program Requirements"] = min(pos for lbl, pos in starts if lbl.startswith("Synopsis of Program"))

    def next_boundary(after_idx: int) -> int:
        next_indices: List[int] = []
        for _, pos in starts:
            if pos > after_idx:
                next_indices.append(pos)
        for j in range(after_idx + 1, len(lines)):
            if roman_boundary.match(lines[j]):
                next_indices.append(j)
                break
        return min(next_indices) if next_indices else len(lines)

    pieces: List[str] = []
    found: List[str] = []
    for label in order:
        if label not in first_pos:
            continue
        start = first_pos[label]
        end = next_boundary(start)
        block_lines = lines[start:end]
        content_lines = block_lines[1:] if len(block_lines) > 1 else []
        content = "\n".join(content_lines).strip()
        if content:
            pieces.append(f"{label}\n\n{content}")
            found.append(label)
    return "\n\n".join(pieces).strip(), found


def _extract_selected_sections(text: str) -> str:
    sel, _ = _select_sections(text)
    return sel


def _parse_structured_from_text(text: str) -> Dict[str, str]:
    found: Dict[str, str] = {}
    m = re.search(r"\bNSF\s*-?\s*(\d{2,}-\d{2,})\b", text, flags=re.I)
    if m:
        found["Solicitation Number"] = f"NSF {m.group(1)}"
    m = re.search(r"Estimated Number of Awards\s*:?\s*([0-9,]+)\b", text, flags=re.I)
    if m:
        found["Estimated Number of Awards"] = m.group(1)
    for label in (
        "Anticipated Funding Amount",
        "Estimated Total Program Funding",
        "Award Ceiling",
        "Award Floor",
    ):
        m = re.search(label + r"\s*:?\s*([^\n]+)", text, flags=re.I)
        if m:
            found[label] = re.sub(r"\s+", " ", m.group(1)).strip()
    return found


def build_text_from_row(
    row: Dict[str, str],
    url_key: Optional[str],
    title_key: str,
    fetch: bool,
    *,
    require_all_sections: bool = False,
) -> Optional[str]:
    headers = [k for k in row.keys()]
    def _get(d: Dict[str, str], name: Optional[str]) -> str:
        return (d.get(name) or "").strip() if name else ""
    title_val = _get(row, title_key)
    url_val = _get(row, url_key)
    lines: List[str] = []
    if url_val:
        lines.append(url_val)
        lines.append("")
    if title_val:
        lines.append(f"Title: {title_val}")
    for h in headers:
        if h == url_key:
            continue
        v = _get(row, h)
        if v:
            lines.append(f"{h}: {v}")
    if fetch and url_val:
        status, body = http_get(url_val, timeout=45)
        if status == 200 and body:
            html = body.decode("utf-8", errors="ignore")
            title, text = extract_text_from_html(html)
            if title and not title_val:
                lines.append("")
                lines.append(f"Detected Title: {title}")
            if text:
                selected, found_labels = _select_sections(text)
                if require_all_sections and set(found_labels) & {"I. Introduction", "II. Program Description", "III. Award Information", "IV. Eligibility Information"} != {"I. Introduction", "II. Program Description", "III. Award Information", "IV. Eligibility Information"}:
                    return None
                if selected:
                    lines.append("")
                    lines.append("Extracted from solicitation page (selected sections):")
                    lines.append(selected)
    return "\n".join(lines).rstrip() + "\n"


def unique_path(out_dir: Path, base_stem: str) -> Path:
    p = out_dir / f"{base_stem}.txt"
    if not p.exists():
        return p
    i = 2
    while True:
        q = out_dir / f"{base_stem}_{i}.txt"
        if not q.exists():
            return q
        i += 1


def _is_grant_row(row: Dict[str, str], headers: Sequence[str]) -> bool:
    type_key = _best_column(headers, ["type"]) or "Type"
    sol_key = _best_column(headers, ["solicitation url", "solicitation link", "solicitation"]) or "Solicitation URL"
    tval = (row.get(type_key) or "").strip().lower()
    if "dear colleague" in tval:
        return False
    sol = (row.get(sol_key) or "").strip()
    if not (sol.startswith("http://") or sol.startswith("https://")):
        return False
    return True


def process_csv(
    csv_path: Path,
    out_dir: Path,
    *,
    fetch: bool,
    overwrite: bool,
    limit: Optional[int] = None,
    skip: int = 0,
    prune_skipped: bool = False,
    require_all_sections: bool = False,
) -> Tuple[int, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no headers")
        headers = [h.strip() for h in reader.fieldnames]
        title_key = _best_column([h for h in headers], ["title", "opportunity title", "name", "program title"])    
        if not title_key:
            raise ValueError("Could not find a Title column (tried: title, opportunity title, name, program title)")
        url_key = _best_column([h for h in headers], ["solicitation url", "solicitation link", "url", "link", "opportunity url", "announcement url", "rfp url"])    
        total = 0
        written = 0
        processed = 0
        for idx, row in enumerate(reader):
            if skip and idx < skip:
                continue
            if limit is not None and processed >= limit:
                break
            total += 1
            if not _is_grant_row(row, headers):
                if prune_skipped:
                    title_val = (row.get(title_key) or "").strip() if title_key else ""
                    stem = "nsf_" + slugify(title_val or f"opportunity_{idx+1}")
                    base = out_dir / f"{stem}.txt"
                    if base.exists():
                        try:
                            base.unlink()
                            print(f"[prune] removed non-grant file {base.name}")
                        except Exception:
                            pass
                continue
            title_val = (row.get(title_key) or "").strip() if title_key else ""
            if not title_val:
                for h in headers:
                    if h == url_key:
                        continue
                    v = (row.get(h) or "").strip()
                    if v:
                        title_val = v
                        break
            stem = "nsf_" + slugify(title_val or f"opportunity_{total}")
            content = build_text_from_row(
                row,
                url_key,
                title_key or "",
                fetch or require_all_sections,
                require_all_sections=require_all_sections,
            )
            if content is None:
                if prune_skipped:
                    out_path = out_dir / f"{stem}.txt"
                    if out_path.exists():
                        try:
                            out_path.unlink()
                            print(f"[prune] removed incomplete-section file {out_path.name}")
                        except Exception:
                            pass
                print(f"[skip] missing required sections for {stem}")
                continue
            out_path = out_dir / f"{stem}.txt"
            if out_path.exists() and not overwrite:
                out_path = unique_path(out_dir, stem)
            out_path.write_text(content, encoding="utf-8")
            written += 1
            print(f"[ok] {out_path.name}")
            processed += 1
            if fetch and (processed % 5 == 0):
                time.sleep(0.2)
    return total, written


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build grant text files from a CSV and optional solicitation URLs.")
    p.add_argument("--csv", help="Path to CSV file or directory containing a CSV (default: data/grants/NSF_database*.csv)")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory (default: data/grants)")
    p.add_argument("--no-fetch", action="store_true", help="Do not fetch solicitation URLs for page text")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing files instead of uniquifying")
    p.add_argument("--limit", type=int, help="Limit to the first N rows (after skipping)")
    p.add_argument("--skip", type=int, default=0, help="Skip the first N data rows before processing")
    p.add_argument("--prune-skipped", action="store_true", help="Delete any existing .txt for rows filtered out (non-grants or incomplete sections)")
    p.add_argument("--require-all-sections", action="store_true", help="Include only rows where I–IV sections are found on the solicitation page")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    try:
        csv_path = _resolve_csv_path(args.csv)
    except Exception as e:
        print(f"[error] {e}")
        return 2
    out_dir = Path(args.out_dir)
    fetch = not args.no_fetch
    try:
        total, written = process_csv(
            csv_path,
            out_dir,
            fetch=fetch,
            overwrite=args.overwrite,
            limit=args.limit,
            skip=args.skip,
            prune_skipped=args.prune_skipped,
            require_all_sections=args.require_all_sections,
        )
        print(f"[done] processed {total} rows → wrote {written} files to {out_dir}")
        return 0
    except Exception as e:
        print(f"[error] {e}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

