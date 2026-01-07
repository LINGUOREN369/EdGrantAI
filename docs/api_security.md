# API Security Overview (EdGrantAI Chat)

This document explains how the EdGrantAI chat endpoint is protected end-to-end,
from the browser to the matching backend.

## Components

- Frontend: `https://linguoren.com/#/edgrantai-chat`
- Cloudflare Worker (edge gateway): `https://edgrantai-proxy.lren-31b.workers.dev/recommend`
- Render API (backend): `https://edgrantai-api.onrender.com/recommend`

## Request Flow

1) User submits a mission in the browser.
2) Turnstile runs in the browser and returns a short-lived token.
3) Browser sends mission + Turnstile token to the Worker.
4) Worker validates Origin, Turnstile token, and rate limits the client.
5) Worker injects `EDGRANT_API_TOKEN` and forwards to Render.
6) Render validates the token and uses `OPENAI_API_KEY` for matching.
7) Recommendations flow back to the browser.

## Secrets and Where They Live

- `OPENAI_API_KEY`: Render only.
- `EDGRANT_API_TOKEN`: Worker + Render only.
- `TURNSTILE_SECRET`: Worker only.
- `TURNSTILE_SITE_KEY`: Frontend (public by design).

The browser never sees or stores any private keys.

## Protections in Place

- Origin allowlist: only `https://linguoren.com` (and `https://www.linguoren.com`) are accepted.
- Turnstile verification: blocks spoofed requests without a valid browser token.
- Rate limiting: throttles abusive traffic per IP.
- Backend auth: Render accepts only requests with a valid token.

## Operational Checklist

- Render env vars:
  - `OPENAI_API_KEY`
  - `EDGRANT_API_TOKEN`
  - `ALLOWED_ORIGINS=https://linguoren.com,https://www.linguoren.com`
- Worker secrets/vars:
  - `TURNSTILE_SECRET`
  - `EDGRANT_API_TOKEN`
  - `BACKEND_URL=https://edgrantai-api.onrender.com`
  - `ALLOWED_ORIGIN=https://linguoren.com,https://www.linguoren.com`

## Notes

- The Worker URL is public by design. Security is enforced by Origin checks,
  Turnstile validation, and the backend token.
- If any key is exposed, rotate it and redeploy.
