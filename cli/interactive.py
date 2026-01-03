from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import time

from common.config import settings
from mapping.org_profile_builder import build_org_profile, save_org_profile
from matching.matching_engine import recommend


def _prompt(msg: str, default: str | None = None) -> str:
    sfx = f" [{default}]" if default else ""
    try:
        inp = input(f"{msg}{sfx}: ").strip()
    except EOFError:
        inp = ""
    return inp or (default or "")


def _prompt_multiline(msg: str, end_token: str = "END") -> str:
    print(msg)
    print(f"(Finish by entering a line with only '{end_token}')")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == end_token:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _sanitize_org_id(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_\-]", "", s)
    return s or "org_input"


def _shorten(text: str | None, max_len: int = 180) -> str:
    if not text:
        return ""
    t = text.strip().replace("\n", " ")
    return t if len(t) <= max_len else (t[: max_len - 1] + "…")


def _print_pretty(result: dict) -> None:
    org_label = result.get("org_profile")
    header = _shorten(org_label, 120)
    print("\n=== Recommendations (preview) ===")
    if header:
        print(f"Org: {header}")
    recs = result.get("recommendations", []) or []
    if not recs:
        print("(no recommendations)")
        return
    for idx, r in enumerate(recs, start=1):
        if not isinstance(r, dict):
            continue
        name = r.get("grant_profile") or "(unknown)"
        score = r.get("score")
        bucket = r.get("bucket")
        deadline = r.get("deadline")
        dnote = r.get("deadline_note")
        funding = r.get("anticipated_funding_amount")
        url = r.get("url")
        expl = r.get("explanation")
        syn = r.get("synopsis")
        print(f"\n{idx}. {name}")
        if score is not None or bucket:
            print(f"   - score: {score if score is not None else 'n/a'}   bucket: {bucket or 'n/a'}")
        if deadline:
            print(f"   - deadline: {deadline}")
        else:
            if dnote:
                print(f"   - deadline: n/a ({dnote})")
            else:
                print("   - deadline: n/a")
        if funding:
            print(f"   - anticipated: {funding}")
        if url:
            print(f"   - url: {url}")
        if expl:
            print(f"   - explanation: {_shorten(expl, 200)}")
        elif syn:
            print(f"   - synopsis: {_shorten(syn, 200)}")

def run() -> int:
    parser = argparse.ArgumentParser(description="Interactive pipeline: enter org profile text → recommendations report.")
    parser.add_argument("--top", type=int, default=10, help="Top-N results to return.")
    parser.add_argument("--no-explain", action="store_true", help="Do not include LLM explanations.")
    parser.add_argument("--out-dir", default=str((settings.REPO_ROOT / "reports").resolve()), help="Directory for the output report JSON.")
    args = parser.parse_args()

    org_text = _prompt_multiline(
        "Paste/type the organization mission and profile text",
        end_token="END",
    )
    if not org_text:
        print("[error] No organization text provided.")
        return 2

    # Derive an org_id from the paragraph (first few words), for filenames only
    first_line = org_text.splitlines()[0] if org_text.splitlines() else org_text
    first_words = " ".join(first_line.strip().split()[:6]) or "org_input"
    org_id = _sanitize_org_id(first_words)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    total_t0 = time.time()

    # Step 1: Extract + map organization info
    print("[step 1/4] Extracting and mapping organization information…", flush=True)
    t0 = time.time()
    profile = build_org_profile(org_id, org_text, source_path=None, source_url=None)
    print(f"[ok] extracted ({time.time()-t0:.2f}s)", flush=True)

    # Step 2: Build (save) organization profile
    print("[step 2/4] Building organization profile (saving)…", flush=True)
    t0 = time.time()
    org_profile_path = save_org_profile(profile)
    print(f"[ok] saved → {org_profile_path} ({time.time()-t0:.2f}s)", flush=True)

    # Run recommendations
    grants_dir = settings.PROCESSED_GRANTS_DIR
    print("[step 3/4] Generating recommendations…", flush=True)
    t0 = time.time()
    result = recommend(Path(org_profile_path), grants_dir, top=args.top, explain=(not args.no_explain))
    # Replace org_profile identifier with the original paragraph as requested
    try:
        result["org_profile"] = org_text
    except Exception:
        pass
    print(f"[ok] recommendations ready ({time.time()-t0:.2f}s)", flush=True)

    # Write report
    out_path = out_dir / f"{org_id}_recommendations.json"
    print("[step 4/4] Writing report…", flush=True)
    t0 = time.time()
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[ok] Wrote recommendations → {out_path} ({time.time()-t0:.2f}s)")
    print(f"[done] Total elapsed: {time.time()-total_t0:.2f}s")
    _print_pretty(result)
    return 0


def _main() -> int:
    try:
        return run()
    except KeyboardInterrupt:
        print("\n[abort] interrupted by user")
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
