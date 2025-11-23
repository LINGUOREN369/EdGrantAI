from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def fetch_html(url: str, wait_selector: Optional[str] = None, timeout_ms: int = 10000, headless: Optional[bool] = None) -> str:
    """
    Fetch page HTML via Playwright (Chromium).

    Args:
        url: Page URL.
        wait_selector: Optional CSS selector to wait for.
        timeout_ms: Max wait in milliseconds.
        headless: Override headless mode; defaults to env PLAYWRIGHT_HEADLESS.
    Returns:
        HTML content as string.
    """
    from playwright.sync_api import sync_playwright

    if headless is None:
        headless = os.getenv("PLAYWRIGHT_HEADLESS", "1") == "1"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=timeout_ms)
        html = page.content()
        context.close()
        browser.close()
        return html


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--wait", default=None, help="CSS selector to wait for")
    args = ap.parse_args()
    print(fetch_html(args.url, wait_selector=args.wait))

