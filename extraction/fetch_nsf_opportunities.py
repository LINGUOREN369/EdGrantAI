"""Fetch NSF funding opportunities pages from nsf.gov into data/grants/."""

from __future__ import annotations

import argparse
import html as ihtml
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple

from common.config import settings


DEFAULT_OUT_DIR = (settings.REPO_ROOT / "data" / "grants").resolve()


def http_get(url: str, *, timeout: int = 30) -> Tuple[int, bytes]:
    headers = {
        "User-Agent": "EdGrantAI/1.0 (+https://github.com/)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close",
    }
    try:
        import requests  # type: ignore
        r = requests.get(url, headers=headers, timeout=timeout)
        return r.status_code, r.content or b""
    except Exception:
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


def url_join(base: str, url: str) -> str:
    from urllib.parse import urljoin
    return urljoin(base, url)


def is_opportunity_url(url: str) -> bool:
    return "/funding/opportunities" in url and not url.rstrip("/").endswith("/funding/opportunities")


def canonical_url(url: str) -> str:
    from urllib.parse import urlsplit, urlunsplit
    parts = list(urlsplit(url))
    parts[3] = ""
    parts[4] = ""
    s = urlunsplit(tuple(parts))
    if s.endswith("/"):
        s = s[:-1]
    return s


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
    KEEP_TAGS = {"main", "article", "section", "p", "li", "ul", "ol", "h1", "h2", "h3", "h4"}
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
        text = re.sub(r"\s+", " ", text)
        text = ihtml.unescape(text)
        paras = [p.strip() for p in text.split("\n")]
        paras = [p for p in paras if p]
        return "\n\n".join(paras).strip()


def _bs4_extract(html: str) -> Tuple[Optional[str], str]:
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except Exception:
        return None, ""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
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
    if status != 200 or not body:
        return None
    return body


def _parse_sitemap_for_urls(xml_bytes: bytes) -> List[str]:
    import xml.etree.ElementTree as ET
    out: List[str] = []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return out
    for url in root.findall(".//{*}url"):
        loc = url.find("{*}loc")
        if loc is not None and loc.text:
            out.append(loc.text.strip())
    for smap in root.findall(".//{*}sitemap"):
        loc = smap.find("{*}loc")
        if loc is not None and loc.text:
            out.append(loc.text.strip())
    return out


def collect_opportunity_links(max_links: int = 500) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    # Try sitemaps first
    for smurl in SITEMAPS:
        xml = _fetch_xml(smurl)
        if not xml:
            continue
        for url in _parse_sitemap_for_urls(xml):
            urlc = canonical_url(url)
            if is_opportunity_url(urlc) and urlc not in seen:
                seen.add(urlc)
                out.append(urlc)
                if len(out) >= max_links:
                    return out
    # Fallback: crawl the listing pages for links
    for base in SEEDS:
        status, body = http_get(base, timeout=45)
        if status != 200 or not body:
            continue
        html = body.decode("utf-8", errors="ignore")
        try:
            from bs4 import BeautifulSoup  # type: ignore
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = None
        if soup is not None:
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
        from urllib.parse import urlsplit
        path = urlsplit(self.url).path.rstrip("/")
        seg = path.split("/")[-1] if path else "opportunity"
        base = f"nsf_{seg}" if seg else "nsf_opportunity"
        return re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_")

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
    if status != 200 or not body:
        return None
    html = body.decode("utf-8", errors="ignore")
    try:
        title, text = _bs4_extract(html)
        if text:
            return OpportunityPage(url=url, title=title, text=text)
    except Exception:
        pass
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

