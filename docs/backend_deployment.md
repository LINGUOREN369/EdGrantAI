# Backend Deployment (Render + Cloudflare Worker)

This guide deploys the EdGrantAI API on Render and protects it behind a Cloudflare Worker proxy so only your website can call it.

---

## 1) Render deployment (EdGrantAI)

Create a new Render Web Service from the EdGrantAI repo:

- Build command:
  - `pip install -r requirements.txt`
- Start command:
  - `gunicorn api.server:app --bind 0.0.0.0:$PORT`

Set environment variables in Render:

- `OPENAI_API_KEY` = your OpenAI key
- `EDGRANT_API_TOKEN` = long random token (keep private)
- `ALLOWED_ORIGINS` = `https://linguoren.com`

Optional: use the provided `render.yaml` for one-click setup.

Health check:
- `GET /health`

---

## 2) Cloudflare Worker proxy

The Worker holds the API token and forwards requests to Render. Your website calls the Worker instead of Render directly.

Deploy:

- `cd worker`
- `wrangler deploy`

Set Worker secrets:

- `wrangler secret put EDGRANT_API_TOKEN`

Set Worker vars (wrangler.toml or dashboard):

- `BACKEND_URL` = `https://<your-render-app>.onrender.com`
- `ALLOWED_ORIGIN` = `https://linguoren.com`

Worker endpoint:
- `https://<worker-name>.workers.dev/recommend`

---

## 3) Website configuration

Set the frontend to call the Worker endpoint:

- `REACT_APP_EDGRANT_API_URL=https://<worker-name>.workers.dev/recommend`

This value can be set in your site build environment or pasted into the chat UI.

---

## 4) Security notes

- Never store `OPENAI_API_KEY` in GitHub or the frontend repo.
- Keep the Render API token secret; only the Worker should send it.
- Use CORS allowlisting and the API token together for defense in depth.

---

## 5) Local development (optional)

Run the API locally:

- `export OPENAI_API_KEY=...`
- `export EDGRANT_API_TOKEN=...`
- `export ALLOWED_ORIGINS=http://localhost:3000`
- `python api/server.py`

Then point the chat UI to:
- `http://localhost:5000/recommend`
