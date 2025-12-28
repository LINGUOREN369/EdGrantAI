"""
Fetch NSF awarded grants via the public NSF Awards API and save as text files
under data/grants/ that the existing pipeline can process.

Endpoint: https://api.nsf.gov/services/v1/awards.json
This public endpoint does not require an API key.

Examples:
- python -m pipeline.fetch_nsf_awards --since 2024-01-01 --max 2000
- make nsf-awards-download  (see Makefile target)

Notes:
- Writes one .txt per award: first line is the award detail URL so the
  grant_profile_builder uses it as `source.url` automatically.
- Page through results using `offset` and `limit`. The API caps throughput;
  a small pause is used to be polite.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from .config import settings

DEFAULT_OUT_DIR = (settings.REPO_ROOT / "data" / "grants").resolve()


def _http_get(url: str, *, timeout: int = 30, headers: Optional[Dict[str, str]] = None) -> Tuple[int, bytes]:
    import urllib.request
    import urllib.error

    req = urllib.request.Request(url, headers=headers or {})
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


def _parse_date(s: Optional[str]) -> Optional[dt.date]:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None


def _fmt_date(d: Optional[dt.date]) -> Optional[str]:
    return d.strftime("%Y-%m-%d") if d else None


@dataclass
class Award:
    id: str
    title: Optional[str]
    abstract: Optional[str]
    pi: Optional[str]
    institution: Optional[str]
    directorate: Optional[str]
    division: Optional[str]
    effective_date: Optional[str]
    expiration_date: Optional[str]
    amount: Optional[str]
    program_codes: List[str]
    award_url: str
    raw: Dict

    @staticmethod
    def from_json(d: Dict) -> "Award":
        # NSF awards API (api.nsf.gov/services/v1/awards.json) uses keys like:
        # id, title, abstractText, piFirstName, piLastName, awardeeName,
        # directorate, division, date, expDate, awardAmount, fundProgramName,
        # programElementCode (list), etc.
        def g(k: str, default=None):
            return d.get(k, default)

        award_id = str(g("id", g("awardID", g("awardId", ""))))
        pi = None
        first = g("piFirstName") or g("pdPIFirstName")
        last = g("piLastName") or g("pdPILastName")
        if first or last:
            pi = f"{first or ''} {last or ''}".strip()
        award_url = f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={award_id}"
        prog_codes: List[str] = []
        pe = g("programElementCode")
        if isinstance(pe, list):
            prog_codes = [str(x) for x in pe]
        elif isinstance(pe, (str, int)):
            prog_codes = [str(pe)]

        return Award(
            id=award_id,
            title=g("title"),
            abstract=g("abstractText"),
            pi=pi,
            institution=g("awardeeName") or g("institution"),
            directorate=g("directorate") or g("directorateCode"),
            division=g("division") or g("divisionCode"),
            effective_date=g("date") or g("effectiveDate"),
            expiration_date=g("expDate") or g("expirationDate"),
            amount=str(g("awardAmount")) if g("awardAmount") is not None else None,
            program_codes=prog_codes,
            award_url=award_url,
            raw=d,
        )

    def to_text(self) -> str:
        lines: List[str] = []
        # First line URL recognized by the grant_profile_builder as source.url
        lines.append(self.award_url)
        lines.append("")

        if self.title:
            lines.append(f"Title: {self.title}")
        lines.append(f"Award ID: {self.id}")
        if self.pi:
            lines.append(f"Principal Investigator: {self.pi}")
        if self.institution:
            lines.append(f"Institution: {self.institution}")
        if self.directorate:
            lines.append(f"Directorate: {self.directorate}")
        if self.division:
            lines.append(f"Division: {self.division}")
        if self.amount:
            lines.append(f"Award Amount: {self.amount}")
        if self.effective_date:
            lines.append(f"Effective Date: {self.effective_date}")
        if self.expiration_date:
            lines.append(f"Expiration Date: {self.expiration_date}")
        if self.program_codes:
            lines.append(f"Program Codes: {', '.join(self.program_codes)}")

        lines.append("")
        if self.abstract:
            lines.append("Abstract:")
            lines.append(self.abstract.strip())
            lines.append("")

        try:
            lines.append("---")
            lines.append("Raw JSON (excerpt):")
            raw_small = {k: self.raw.get(k) for k in list(self.raw.keys())[:30]}
            lines.append(json.dumps(raw_small, indent=2))
        except Exception:
            pass

        return "\n".join(lines).rstrip() + "\n"


def _build_url(offset: int, limit: int, since: Optional[dt.date], until: Optional[dt.date]) -> str:
    from urllib.parse import urlencode

    base = "https://api.nsf.gov/services/v1/awards.json"
    q: Dict[str, str] = {
        "offset": str(offset),  # API uses 1-based offsets
        "limit": str(limit),
    }
    if since:
        q["dateStart"] = _fmt_date(since) or ""
    if until:
        q["dateEnd"] = _fmt_date(until) or ""
    return f"{base}?{urlencode(q)}"


def _fetch_page(offset: int, limit: int, since: Optional[dt.date], until: Optional[dt.date]) -> List[Award]:
    url = _build_url(offset, limit, since, until)
    status, body = _http_get(url, timeout=45, headers={"User-Agent": "EdGrantAI/1.0 (+https://github.com/)"})
    if status == 0:
        print("[warn] network blocked or unreachable when calling NSF Awards API")
        return []
    if status != 200:
        return []
    try:
        data = json.loads(body.decode("utf-8"))
    except Exception:
        return []

    # Expected structure: {response: {award: [ ... ]}}
    items = []
    if isinstance(data, dict):
        resp = data.get("response") if isinstance(data.get("response"), dict) else data
        if isinstance(resp, dict):
            aw = resp.get("award")
            if isinstance(aw, list):
                items = aw
    elif isinstance(data, list):
        items = data

    awards: List[Award] = []
    for item in items:
        if isinstance(item, dict):
            awards.append(Award.from_json(item))
    return awards


def iter_awards(
    *,
    since: Optional[dt.date],
    until: Optional[dt.date],
    limit: int = 100,
    max_records: int = 10000,
    pause_s: float = 0.2,
) -> Iterator[Award]:
    offset = 1  # NSF API nominally uses 1-based offset; try 0 as fallback if empty
    yielded = 0
    tried_zero = False
    while True:
        items = _fetch_page(offset, limit, since, until)
        if not items:
            if offset == 1 and not tried_zero:
                # Some environments/APIs may expect 0-based offset
                tried_zero = True
                offset = 0
                continue
            break
        for aw in items:
            yield aw
            yielded += 1
            if yielded >= max_records:
                return
        offset += limit
        time.sleep(pause_s)


def write_award(out_dir: Path, aw: Award, *, overwrite: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"nsf_award_{aw.id}"
    out_path = out_dir / f"{stem}.txt"
    if out_path.exists() and not overwrite:
        return out_path
    out_path.write_text(aw.to_text(), encoding="utf-8")
    return out_path


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download NSF awards into data/grants using the public NSF Awards API.")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory (default: data/grants)")
    p.add_argument("--since", help="Only include awards with effective date on/after this (YYYY-MM-DD)")
    p.add_argument("--until", help="Only include awards with effective date on/before this (YYYY-MM-DD)")
    p.add_argument("--max", type=int, default=2000, help="Maximum awards to fetch (default 2000)")
    p.add_argument("--page-size", type=int, default=100, help="Page size (default 100)")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    p.add_argument("--dry-run", action="store_true", help="List awards instead of writing files")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    out_dir = Path(args.out_dir)
    since = _parse_date(args.since) if args.since else None
    until = _parse_date(args.until) if args.until else None
    page_size = max(1, int(args.page_size))
    max_records = max(1, int(args.max))

    print(f"[awards] since={since} until={until} page_size={page_size} max={max_records}")

    count = 0
    written = 0
    for aw in iter_awards(since=since, until=until, limit=page_size, max_records=max_records):
        count += 1
        if args.dry_run:
            print(f"- nsf_award_{aw.id} :: {aw.title or ''} → {aw.award_url}")
            continue
        try:
            path = write_award(out_dir, aw, overwrite=args.overwrite)
            written += 1
            print(f"[ok] {path.name}")
        except Exception as e:
            print(f"[warn] failed to write nsf_award_{aw.id}: {e}")

    if args.dry_run:
        print(f"[done] listed {count} awards (no files written)")
    else:
        print(f"[done] processed {count} awards, wrote {written} files to {out_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
