"""
Fetch NSF funding opportunities directly from nsf.gov pages and save to data/grants/.

Seeds:
- https://www.nsf.gov/funding/opportunities
- https://new.nsf.gov/funding/opportunities

Approach:
- Prefer sitemaps for comprehensive discovery, then fall back to listing pages.
- For each detail page, fetch HTML and extract readable text.
- Writes a .txt file per page with the source URL as the first line (compatible with the
  grant profile builder which auto-detects the URL on line 1).

Dependencies:
- Works with stdlib only (urllib + html.parser), but will use BeautifulSoup and requests
  when available (see requirements.txt) for more robust parsing.
"""

from __future__ import annotations

import argparse
import html as ihtml
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .config import settings

# Optional dependencies for better crawling and parsing
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


# -------------------------------------------------------------
# HTTP helpers
# -------------------------------------------------------------
def http_get(url: str, *, timeout: int = 30) -> Tuple[int, bytes]:
    """HTTP GET with requests if available, else urllib.

    Returns (status_code, body_bytes). 0 means blocked/unreachable.
    """
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


# -------------------------------------------------------------
# URL/HTML utils
# -------------------------------------------------------------
def url_join(base: str, url: str) -> str:
    from urllib.parse import urljoin

    return urljoin(base, url)


def is_opportunity_url(url: str) -> bool:
    # Accept both new and legacy sites; focus on '/funding/opportunities'
    return "/funding/opportunities" in url and not url.rstrip("/").endswith("/funding/opportunities")


def canonical_url(url: str) -> str:
    # Strip fragments and normalize trailing slash
    from urllib.parse import urlsplit, urlunsplit

    parts = list(urlsplit(url))
    parts[3] = ""  # drop query
    parts[4] = ""  # drop fragment
    s = urlunsplit(tuple(parts))
    if s.endswith("/"):
        s = s[:-1]
    return s


def slugify(s: str, max_len: int = 80) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return (s[:max_len].rstrip("_") or "opportunity")


# -------------------------------------------------------------
# HTML parsing (links + visible text)
# -------------------------------------------------------------
class LinkExtractor:
    def __init__(self) -> None:
        self.links: List[str] = []

    def feed(self, html: str) -> None:
        from html.parser import HTMLParser

        extractor = self

        class _P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag.lower() == "a":
                    href = None
                    for k, v in attrs:
                        if k.lower() == "href":
                            href = v
                            break
                    if href:
                        extractor.links.append(href)

        _P().feed(html)


class TextExtractor:
    """Collect readable text from main/article/section/p/li and headings.

    Skips script/style/nav/footer/header.
    """

    KEEP_TAGS = {
        "main",
        "article",
        "section",
        "p",
        "li",
        "ul",
        "ol",
        "h1",
        "h2",
        "h3",
        "h4",
    }
    SKIP_TAGS = {"script", "style", "nav", "footer", "header", "noscript"}

    def __init__(self) -> None:
        self._buf: List[str] = []
        self._skip_stack: List[str] = []
        self._keep_depth = 0

    def feed(self, html: str) -> None:
        from html.parser import HTMLParser

        te = self

        class _P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                tl = tag.lower()
                if tl in TextExtractor.SKIP_TAGS:
                    te._skip_stack.append(tl)
                    return
                if tl in TextExtractor.KEEP_TAGS:
                    te._keep_depth += 1

            def handle_endtag(self, tag):
                tl = tag.lower()
                if te._skip_stack and te._skip_stack[-1] == tl:
                    te._skip_stack.pop()
                    return
                if tl in TextExtractor.KEEP_TAGS and te._keep_depth > 0:
                    te._keep_depth -= 1
                    te._buf.append("\n")

            def handle_data(self, data):
                if te._skip_stack:
                    return
                if te._keep_depth > 0:
                    text = data.strip()
                    if text:
                        te._buf.append(text)

        _P().feed(html)

    def get_text(self) -> str:
        text = " ".join(self._buf)
        # Collapse whitespace and unescape entities
        text = re.sub(r"\s+", " ", text)
        text = ihtml.unescape(text)
        # Form paragraphs by splitting on sentinel newlines we added
        paras = [p.strip() for p in text.split("\n")]
        paras = [p for p in paras if p]
        return "\n\n".join(paras).strip()


def _bs4_extract(html: str) -> Tuple[Optional[str], str]:
    """Extract (title, text) via BeautifulSoup, when installed."""
    if not HAVE_BS4:
        return None, ""
    # Prefer lxml if present
    parser = "lxml"
    try:
        soup = BeautifulSoup(html, parser)
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # Remove non-content nodes
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

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

    lines: List[str] = []
    for root in containers:
        for el in root.select("h2, h3, h4, p, li"):
            txt = el.get_text(" ", strip=True)
            if txt:
                lines.append(txt)
        if lines:
            break

    if not lines:
        txt = soup.get_text(" ", strip=True)
        if txt:
            lines = [txt]

    # Collapse whitespace and dedupe consecutive repeats
    clean: List[str] = []
    prev = None
    for seg in lines:
        seg = re.sub(r"\s+", " ", seg).strip()
        if not seg:
            continue
        if prev is None or seg != prev:
            clean.append(seg)
        prev = seg

    body = "\n\n".join(clean).strip()
    return title, body


# -------------------------------------------------------------
# Core fetch logic
# -------------------------------------------------------------
SEEDS = [
    "https://www.nsf.gov/funding/opportunities",
    "https://new.nsf.gov/funding/opportunities",
]

SITEMAPS = [
    "https://new.nsf.gov/sitemap.xml",
    "https://www.nsf.gov/sitemap.xml",
]


def _fetch_xml(url: str) -> Optional[bytes]:
    status, body = http_get(url, timeout=45)
    if status == 0:
        print("[warn] network blocked or unreachable when fetching sitemap:", url)
        return None
    if status != 200 or not body:
        print(f"[warn] failed to fetch sitemap: {url} (status {status})")
        return None
    return body


def _parse_sitemap_for_urls(xml_bytes: bytes) -> List[str]:
    import xml.etree.ElementTree as ET

    out: List[str] = []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return out

    # Namespaces commonly used in sitemaps
    ns = {
        "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "image": "http://www.google.com/schemas/sitemap-image/1.1",
        "news": "http://www.google.com/schemas/sitemap-news/0.9",
        "video": "http://www.google.com/schemas/sitemap-video/1.1",
    }

    # Try urlset first
    for url in root.findall(".//{*}url"):
        loc = url.find("{*}loc")
        if loc is not None and loc.text:
            out.append(loc.text.strip())

    # Or sitemapindex (nested sitemaps)
    for smap in root.findall(".//{*}sitemap"):
        loc = smap.find("{*}loc")
        if loc is not None and loc.text:
            out.append(loc.text.strip())

    return out


def collect_opportunity_links_from_sitemaps(max_links: int) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []

    nested_sitemaps: List[str] = []
    # Fetch root sitemaps
    for smap in SITEMAPS:
        xml_bytes = _fetch_xml(smap)
        if not xml_bytes:
            continue
        urls = _parse_sitemap_for_urls(xml_bytes)
        for u in urls:
            if u.endswith(".xml"):
                nested_sitemaps.append(u)
            elif is_opportunity_url(u):
                cu = canonical_url(u)
                if cu not in seen:
                    seen.add(cu)
                    out.append(cu)
                    if len(out) >= max_links:
                        return out

    # Walk nested sitemaps
    for smap in nested_sitemaps:
        xml_bytes = _fetch_xml(smap)
        if not xml_bytes:
            continue
        urls = _parse_sitemap_for_urls(xml_bytes)
        for u in urls:
            if u.endswith(".xml"):
                # Depth-2 only
                continue
            if not is_opportunity_url(u):
                continue
            cu = canonical_url(u)
            if cu in seen:
                continue
            seen.add(cu)
            out.append(cu)
            if len(out) >= max_links:
                return out
        time.sleep(0.2)

    return out


def collect_opportunity_links(max_links: int) -> List[str]:
    # Prefer sitemaps for reliability
    links = collect_opportunity_links_from_sitemaps(max_links)
    if links:
        return links
    seen: Set[str] = set()
    out: List[str] = []
    for seed in SEEDS:
        status, body = http_get(seed, timeout=45)
        if status == 0:
            print("[warn] network blocked or unreachable when fetching seed page:", seed)
            continue
        if status != 200 or not body:
            print(f"[warn] failed to fetch listing: {seed} (status {status})")
            continue
        html = body.decode("utf-8", errors="ignore")
        base = seed
        if HAVE_BS4:
            # Use BeautifulSoup for more robust link discovery
            try:
                soup = BeautifulSoup(html, "lxml")
            except Exception:
                soup = BeautifulSoup(html, "html.parser")
            anchors = soup.find_all("a", href=True)
            for a in anchors:
                abs_url = canonical_url(url_join(base, a["href"]))
                if not is_opportunity_url(abs_url):
                    continue
                if abs_url in seen:
                    continue
                seen.add(abs_url)
                out.append(abs_url)
                if len(out) >= max_links:
                    return out
        else:
            # Stdlib fallback
            le = LinkExtractor()
            le.feed(html)
            for href in le.links:
                if not href:
                    continue
                abs_url = canonical_url(url_join(base, href))
                if not is_opportunity_url(abs_url):
                    continue
                if abs_url in seen:
                    continue
                seen.add(abs_url)
                out.append(abs_url)
                if len(out) >= max_links:
                    return out
        time.sleep(0.2)
    return out


@dataclass
class OpportunityPage:
    url: str
    title: Optional[str]
    text: str

    def filename_stem(self) -> str:
        # Prefer a stable slug from the URL last segment; fallback to title
        from urllib.parse import urlsplit

        path = urlsplit(self.url).path.rstrip("/")
        seg = path.split("/")[-1] if path else "opportunity"
        base = f"nsf_{seg}" if seg else "nsf_opportunity"
        return slugify(base)

    def to_text(self) -> str:
        lines: List[str] = []
        lines.append(self.url)
        lines.append("")
        if self.title:
            lines.append(f"Title: {self.title}")
            lines.append("")
        if self.text:
            lines.append(self.text)
        return "\n".join(lines).rstrip() + "\n"


def fetch_opportunity(url: str) -> Optional[OpportunityPage]:
    status, body = http_get(url, timeout=60)
    if status == 0:
        print("[warn] network blocked or unreachable when fetching:", url)
        return None
    if status != 200 or not body:
        print(f"[warn] failed to fetch: {url} (status {status})")
        return None
    html = body.decode("utf-8", errors="ignore")
    # Prefer BeautifulSoup when available
    if HAVE_BS4:
        title, text = _bs4_extract(html)
        if text:
            return OpportunityPage(url=url, title=title, text=text)
    # Fallback to stdlib extractor
    te = TextExtractor()
    te.feed(html)
    text = te.get_text()
    return OpportunityPage(url=url, title=None, text=text)


def write_opportunity(out_dir: Path, opp: OpportunityPage, *, overwrite: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = opp.filename_stem()
    path = out_dir / f"{stem}.txt"
    if path.exists() and not overwrite:
        return path
    path.write_text(opp.to_text(), encoding="utf-8")
    return path


# -------------------------------------------------------------
# CLI
# -------------------------------------------------------------
def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download NSF funding opportunities from nsf.gov into data/grants.")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory (default: data/grants)")
    p.add_argument("--max", type=int, default=5000, help="Maximum opportunities to download (default 5000)")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    p.add_argument("--dry-run", action="store_true", help="List opportunities without saving files")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    out_dir = Path(args.out_dir)
    max_links = max(1, int(args.max))

    links = collect_opportunity_links(max_links)
    if not links:
        print("[warn] no opportunity links found — check network or site structure")
        return 1

    count = 0
    written = 0
    for url in links:
        count += 1
        if args.dry_run:
            print(f"- {url}")
            continue
        page = fetch_opportunity(url)
        if not page:
            continue
        try:
            p = write_opportunity(out_dir, page, overwrite=args.overwrite)
            written += 1
            print(f"[ok] {p.name}")
        except Exception as e:
            print(f"[warn] failed to write {url}: {e}")
        time.sleep(0.3)

    if args.dry_run:
        print(f"[done] listed {count} links (no files written)")
    else:
        print(f"[done] processed {count} pages, wrote {written} files to {out_dir}")
    return 0 if (args.dry_run or written > 0) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
