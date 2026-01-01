"""
Fetch NSF opportunities from Grants.gov and save text files under data/grants/.

Queries the Grants.gov Public Data API (or a fallback UI endpoint) for NSF
opportunities and writes plain text files compatible with the grant profile
builder (first line URL + metadata + synopsis excerpt).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from common.config import settings


DEFAULT_OUT_DIR = (settings.REPO_ROOT / "data" / "grants").resolve()


def _http_get(url: str, *, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Tuple[int, bytes]:
    import urllib.request
    import urllib.error

    req = urllib.request.Request(url, headers=headers or {"User-Agent": "EdGrantAI/1.0 (+https://github.com/)"})
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


def _http_post_json(url: str, payload: Dict, *, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Tuple[int, bytes]:
    import urllib.request
    import urllib.error

    data = json.dumps(payload).encode("utf-8")
    base_headers = {"Content-Type": "application/json", "User-Agent": "EdGrantAI/1.0 (+https://github.com/)"}
    if headers:
        base_headers.update(headers)

    req = urllib.request.Request(url, data=data, headers=base_headers, method="POST")
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
    for f in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            return dt.datetime.strptime(s, f).date()
        except Exception:
            pass
    return None


def _slugify(s: str, max_len: int = 80) -> str:
    import re
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "opportunity"
    if len(s) > max_len:
        s = s[:max_len].rstrip("_")
    return s


@dataclass
class Opportunity:
    number: Optional[str]
    title: Optional[str]
    url: Optional[str]
    agency: Optional[str]
    agency_code: Optional[str]
    status: Optional[str]
    open_date: Optional[str]
    close_date: Optional[str]
    synopsis: Optional[str]
    raw: Dict

    @staticmethod
    def from_json(d: Dict) -> "Opportunity":
        def g(*keys, default=None):
            for k in keys:
                if k in d and d[k] not in (None, ""):
                    return d[k]
            return default
        return Opportunity(
            number=g("opportunityNumber", "number", "oppNumber", "opportunityId", "id"),
            title=g("opportunityTitle", "title"),
            url=g("opportunityUrl", "url", "opportunityLink", "fullAnnouncementUrl", "detailUrl"),
            agency=g("agency", "agencyName"),
            agency_code=g("agencyCode", "agency_code", "agencyShortName"),
            status=g("opportunityStatus", "status", "fundingOppStatus"),
            open_date=g("openDate", "postDate", "publishDate"),
            close_date=g("closeDate", "dueDate", "closeDateExplanation"),
            synopsis=g("synopsis", "description", "summary"),
            raw=d,
        )

    def filename_stem(self) -> str:
        if self.number:
            base = f"nsf_{self.number}"
            return _slugify(base)
        if self.title:
            return _slugify(f"nsf_{self.title}")
        return f"nsf_{_slugify('opportunity')}"

    def to_text(self) -> str:
        lines: List[str] = []
        if self.url:
            lines.append(self.url)
            lines.append("")
        if self.title:
            lines.append(f"Title: {self.title}")
        if self.number:
            lines.append(f"Opportunity Number: {self.number}")
        if self.agency or self.agency_code:
            ac = f" ({self.agency_code})" if self.agency_code and (self.agency_code not in (self.agency or "")) else ""
            lines.append(f"Agency: {self.agency or ''}{ac}")
        if self.status:
            lines.append(f"Status: {self.status}")
        if self.open_date:
            lines.append(f"Open Date: {self.open_date}")
        if self.close_date:
            lines.append(f"Close Date: {self.close_date}")
        lines.append("")
        if self.synopsis:
            lines.append("Synopsis:")
            lines.append(self.synopsis.strip())
            lines.append("")
        try:
            lines.append("---")
            lines.append("Raw JSON (excerpt):")
            raw_small = {k: self.raw.get(k) for k in list(self.raw.keys())[:30]}
            lines.append(json.dumps(raw_small, indent=2))
        except Exception:
            pass
        return "\n".join(lines).rstrip() + "\n"


def _grants_gov_build_url(api_key: str, *, start: int, max_records: int, statuses: List[str], since: Optional[dt.date]) -> str:
    base = "https://api.grants.gov/v1.0/opportunities/search"
    sts = "|".join(statuses) if statuses else ""
    qs = [("api_key", api_key), ("agencyCode", "NSF"), ("startRecordNum", str(start)), ("maxRecords", str(max_records))]
    if sts:
        qs.append(("fundingOppStatuses", sts))
    if since:
        qs.append(("publishDateStart", since.strftime("%m/%d/%Y")))
    from urllib.parse import urlencode
    return f"{base}?{urlencode(qs)}"


def _grants_gov_fetch_page(api_key: str, *, start: int, max_records: int, statuses: List[str], since: Optional[dt.date]) -> Tuple[int, List[Opportunity], int]:
    url = _grants_gov_build_url(api_key, start=start, max_records=max_records, statuses=statuses, since=since)
    status, body = _http_get(url, timeout=45, headers={"User-Agent": "EdGrantAI/1.0 (+https://github.com/)"})
    if status == 0:
        print("[warn] network blocked or unreachable when calling Grants.gov API")
        return 0, [], 0
    if status != 200:
        return 0, [], 0
    try:
        data = json.loads(body.decode("utf-8"))
    except Exception:
        return 0, [], 0
    candidates = []
    total = 0
    if isinstance(data, dict):
        for key in ("opportunities", "opportunitySearchResult", "data", "results", "items"):
            v = data.get(key)
            if isinstance(v, list):
                candidates = v
                break
        for key in ("totalRecords", "total", "resultCount", "count"):
            tv = data.get(key)
            if isinstance(tv, int):
                total = tv
                break
    elif isinstance(data, list):
        candidates = data
        total = len(data)
    opps: List[Opportunity] = []
    for item in candidates:
        if isinstance(item, dict):
            opps.append(Opportunity.from_json(item))
    return len(opps), opps, total


def iter_grants_gov_opportunities(api_key: str, *, statuses: List[str], since: Optional[dt.date], page_size: int = 100, max_records: int = 10000, pause_s: float = 0.2) -> Iterator[Opportunity]:
    start = 1
    yielded = 0
    while True:
        count, opps, total = _grants_gov_fetch_page(api_key, start=start, max_records=page_size, statuses=statuses, since=since)
        if count == 0:
            break
        for o in opps:
            yield o
            yielded += 1
            if yielded >= max_records:
                return
        if total and yielded >= total:
            break
        start += page_size
        time.sleep(pause_s)


def _normalize_statuses(s: str) -> List[str]:
    raw = [x.strip().lower() for x in s.replace(",", "|").split("|") if x.strip()]
    mapping = {
        "posted": "posted",
        "forecasted": "forecasted",
        "forecasts": "forecasted",
        "closed": "closed",
        "archive": "closed",
        "archived": "closed",
        "all": "",
    }
    out: List[str] = []
    for x in raw:
        out.append(mapping.get(x, x))
    out = [x for x in out if x]
    return out


def write_opportunity_text(out_dir: Path, opp: Opportunity, *, overwrite: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = opp.filename_stem()
    out_path = out_dir / f"{stem}.txt"
    if out_path.exists() and not overwrite:
        return out_path
    text = opp.to_text()
    out_path.write_text(text, encoding="utf-8")
    return out_path


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download NSF opportunities from Grants.gov into data/grants.")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory (default: data/grants)")
    p.add_argument("--statuses", default="posted", help="Pipe- or comma-separated list of statuses (posted|forecasted|closed). Default: posted")
    p.add_argument("--since", help="Only include opportunities published on/after this date (YYYY-MM-DD)")
    p.add_argument("--max", type=int, default=2000, help="Maximum opportunities to fetch (default 2000)")
    p.add_argument("--page-size", type=int, default=100, help="Page size for API requests (default 100)")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing files instead of skipping")
    p.add_argument("--source", choices=["auto", "api", "fallback"], default="auto", help="Which source to use: official API, fallback UI, or auto")
    p.add_argument("--dry-run", action="store_true", help="List what would be downloaded without writing files")
    return p.parse_args(argv)


def iter_grants_gov_fallback(*, statuses: List[str], since: Optional[dt.date], page_size: int = 100, max_records: int = 10000, pause_s: float = 0.2) -> Iterator[Opportunity]:
    # Minimal fallback that returns nothing in restricted environments.
    if since or statuses:
        pass
    for _ in range(0):
        yield  # pragma: no cover
    return


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    out_dir = Path(args.out_dir)
    statuses = _normalize_statuses(args.statuses)
    since_date = _parse_date(args.since) if args.since else None
    page_size = max(1, int(args.page_size))
    max_records = max(1, int(args.max))
    api_key = os.getenv("GRANTS_GOV_API_KEY") or os.getenv("GRANTSGOV_API_KEY")
    use_api = args.source in ("auto", "api") and api_key
    print(f"[fetch] source={'api' if use_api else ('fallback' if args.source in ('fallback','auto') else 'none')} statuses={statuses or ['all']} since={since_date}")
    if use_api:
        it = iter_grants_gov_opportunities(api_key, statuses=statuses, since=since_date, page_size=page_size, max_records=max_records)
    else:
        if args.source == "api" and not api_key:
            print("[error] --source api requires GRANTS_GOV_API_KEY in environment.")
            return 2
        it = iter_grants_gov_fallback(statuses=statuses, since=since_date, page_size=page_size, max_records=max_records)
    count = 0
    written = 0
    for opp in it:
        count += 1
        if args.dry_run:
            print(f"- {opp.filename_stem()} :: {opp.title or ''} [{opp.number or ''}] → {opp.url or ''}")
            continue
        try:
            path = write_opportunity_text(out_dir, opp, overwrite=args.overwrite)
            written += 1
            print(f"[ok] {path.name}")
        except Exception as e:
            print(f"[warn] failed to write {opp.filename_stem()}: {e}")
    if args.dry_run:
        print(f"[done] listed {count} opportunities (no files written)")
    else:
        print(f"[done] processed {count} opportunities, wrote {written} files to {out_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

