from __future__ import annotations

from typing import Dict, List

from .match_engine import MatchEngine


def run_matching(project_description: str, top_k: int = 5) -> List[Dict]:
    engine = MatchEngine()
    return engine.match(project_description, top_k=top_k)


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--desc", required=True, help="Project description")
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()
    print(json.dumps(run_matching(args.desc, top_k=args.k), indent=2))

