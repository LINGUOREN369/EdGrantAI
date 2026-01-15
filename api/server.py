from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, make_response, request

from common.config import settings
from mapping.org_profile_builder import build_org_profile, save_org_profile
from matching.matching_engine import recommend


app = Flask(__name__)


def _split_env_list(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _allowed_origin(origin: Optional[str]) -> bool:
    allowed = _split_env_list(os.getenv("ALLOWED_ORIGINS", "http://localhost:3000"))
    if not origin:
        return True
    return origin in allowed


def _cors_headers(origin: Optional[str]) -> dict:
    return {
        "Access-Control-Allow-Origin": origin or "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-EdGrant-Token",
        "Access-Control-Max-Age": "600",
        "Vary": "Origin",
    }


def _auth_ok(req) -> bool:
    expected = os.getenv("EDGRANT_API_TOKEN")
    if not expected:
        return True
    auth = (req.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        return token == expected
    if (req.headers.get("X-EdGrant-Token") or "").strip() == expected:
        return True
    return False


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    chars_per_token = settings.TOKEN_CHARS_PER_TOKEN or 4.0
    if chars_per_token <= 0:
        chars_per_token = 4.0
    return int(math.ceil(len(text) / chars_per_token))


def _count_words(text: str) -> int:
    if not text:
        return 0
    return len(re.findall(r"\S+", text))


def _sanitize_org_id(value: str) -> str:
    s = value.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_\-]", "", s)
    return s or "org_input"


def _derive_org_id(org_name: str, mission: str) -> str:
    if org_name:
        base = org_name
    else:
        first_line = mission.splitlines()[0] if mission.splitlines() else mission
        first_words = " ".join(first_line.strip().split()[:6]) or "org_input"
        base = first_words
    return _sanitize_org_id(base)


def _json_error(message: str, status: int, origin: Optional[str] = None):
    resp = make_response(jsonify({"error": message}), status)
    for k, v in _cors_headers(origin).items():
        resp.headers[k] = v
    return resp


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/recommend", methods=["POST", "OPTIONS"])
def recommend_endpoint():
    origin = request.headers.get("Origin")
    if request.method == "OPTIONS":
        if not _allowed_origin(origin):
            return _json_error("Origin not allowed", 403, origin)
        resp = make_response("", 204)
        for k, v in _cors_headers(origin).items():
            resp.headers[k] = v
        return resp

    if not _allowed_origin(origin):
        return _json_error("Origin not allowed", 403, origin)

    if not _auth_ok(request):
        return _json_error("Unauthorized", 401, origin)

    if not os.getenv("OPENAI_API_KEY"):
        return _json_error("OPENAI_API_KEY is not set", 500, origin)

    data = request.get_json(silent=True) or {}
    mission = (data.get("mission") or "").strip()
    org_name = (data.get("org_name") or "").strip()
    top = data.get("top", 10)
    explain = bool(data.get("explain", False))

    if not mission:
        return _json_error("mission is required", 400, origin)
    token_est = _estimate_tokens(mission)
    if token_est > settings.MAX_MISSION_TOKENS:
        word_count = _count_words(mission)
        word_limit = int(settings.MAX_MISSION_TOKENS * settings.TOKEN_WORDS_PER_TOKEN)
        chars_per_token = settings.TOKEN_CHARS_PER_TOKEN or 4.0
        return _json_error(
            "mission is too long: "
            f"estimated {token_est} tokens (max {settings.MAX_MISSION_TOKENS}). "
            f"Approx word limit {word_limit}; current {word_count} words. "
            f"Token estimate uses ~{chars_per_token:g} chars per token.",
            400,
            origin,
        )

    try:
        top_n = int(top)
    except (TypeError, ValueError):
        top_n = 10
    if top_n < 1:
        top_n = 10
    if top_n > 50:
        top_n = 50

    org_id = _derive_org_id(org_name, mission)
    org_text = f"Organization: {org_name}\nMission: {mission}\n" if org_name else f"Mission: {mission}\n"

    try:
        profile = build_org_profile(org_id, org_text)
    except Exception as exc:
        return _json_error(f"Failed to build org profile: {exc}", 500, origin)

    try:
        org_profile_path = save_org_profile(profile)
        result = recommend(org_profile_path, settings.PROCESSED_GRANTS_DIR, top=top_n, explain=explain)
    except Exception as exc:
        return _json_error(f"Failed to generate recommendations: {exc}", 500, origin)

    result["org_profile"] = org_profile_path.name
    result["org_profile_json"] = profile
    result["org_summary"] = {"name": org_name, "mission": mission}
    resp = make_response(jsonify(result), 200)
    for k, v in _cors_headers(origin).items():
        resp.headers[k] = v
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
