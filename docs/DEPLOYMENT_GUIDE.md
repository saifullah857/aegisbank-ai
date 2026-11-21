# Deployment Guide — Hugging Face Spaces (backend + app) and Vercel (frontend)

**Architecture:** Hugging Face runs ONE container (FastAPI API + the built React app + SQLite). Vercel hosts a second copy of the React app that forwards `/api/*` to the Hugging Face backend (a *rewrite*, so no CORS setup is needed). You can use only Hugging Face (the Space URL already serves the full app); Vercel is optional but gives you a nice `*.vercel.app` link.

```
Browser ──> Vercel (static React)  ──/api/*──>  Hugging Face Space (FastAPI + SQLite + React)
Browser ──> https://USER-SPACE.hf.space        (works on its own too)
```

---
## 0. Before you start (5 min)
1. Create free accounts: <https://huggingface.co>, <https://vercel.com>, <https://github.com>.
2. Install `git` and (optional) Docker. Python 3.12 + Node 22 only if you want to run locally.
3. Generate a JWT secret (keep it private):
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
4. (Optional, free) Groq API key for LLM answers: <https://console.groq.com> → API Keys. Without it the app and chatbot still work (deterministic mode).

## 1. Test locally first (recommended)
```bash
# backend
cd backend
python -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
set -a; . .env.example; set +a                           # or create backend/.env from .env.example
alembic upgrade head && python -m app.db.seed 200 2000
uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend && npm ci && npm run dev                      # http://localhost:5173  (proxies /api to :8000)
```
Login: `analyst01` / `AegisDemo123!`. Run tests: `cd backend && pytest -q` (112 should pass).

Full stack with Docker: copy `.env.example` → `.env`, fill `POSTGRES_PASSWORD` and `JWT_SECRET`, then `docker compose up --build` → <http://localhost:8080>.

## 2. Push the project to GitHub
```bash
cd aegisbank-ai
git init -b main            # skip if it already has a repo
git add . && git commit -m "AegisBank AI: ledger, assistant, deployment"
git remote add origin https://github.com/<you>/aegisbank-ai.git
git push -u origin main
```
`.gitignore` already excludes `venv/`, `node_modules/`, `*.db`. **Never commit `.env`.**

## 3. Deploy the backend + app on Hugging Face Spaces
1. Hugging Face → profile → **Settings → Access Tokens → New token** → role **Write** → copy it.
2. **New Space** (huggingface.co/new-space): name `aegisbank-ai`, **SDK: Docker → Blank**, Hardware **CPU basic (free)**, Visibility **Public**.
3. In the Space: **Settings → Variables and secrets → New secret** (do this BEFORE pushing, otherwise the first start fails with "Refusing to start: JWT_SECRET…"):

   | Secret | Value |
   |---|---|
   | `JWT_SECRET` | the 64-char string from step 0 (**required**) |
   | `DEMO_PASSWORD` | a password of your choice for the demo users (recommended — the default is public in the README) |
   | `GROQ_API_KEY` | optional, enables LLM agents + chatbot answers |

4. Build the Space folder and push:
   ```bash
   bash deploy/huggingface/prepare_space.sh          # creates ./hf_space (no venv/node_modules/db)
   cd hf_space
   git init -b main
   git remote add space https://huggingface.co/spaces/<HF_USERNAME>/aegisbank-ai
   git add . && git commit -m "Deploy AegisBank AI"
   git push space main        # username = your HF username, password = the Write token
   ```
5. Open the Space → **Logs**. First build takes ~5–10 min (pip + npm). When you see `Uvicorn running on http://0.0.0.0:7860` it is live at
   `https://<hf_username>-aegisbank-ai.hf.space` (lowercase; `_` becomes `-`). Check `https://…hf.space/api/v1/health`.

**Things to know about the free tier**
* Container disk is **ephemeral**: on every restart the DB is re-created and re-seeded (300 customers / 3 000 transactions, ~1 min). New payments you make are lost on restart — fine for a demo.
* A Space sleeps after ~48 h without visitors; the first visit wakes it (1–2 min). Open it once before an interview/demo.
* Want permanent data? Create a free Postgres (Neon / Supabase), add secret `DATABASE_URL=postgresql+psycopg2://USER:PASS@HOST/DB?sslmode=require` and `SEED_ON_START=false` after the first seed.
* Update the app later: re-run `prepare_space.sh`, then commit & push inside `hf_space` (or copy changes into your existing Space clone).

## 4. Deploy the frontend on Vercel (optional)
1. Edit **`frontend/vercel.json`** and replace `YOUR-HF-USERNAME-YOUR-SPACE-NAME` with your real Space host, e.g.
   `https://zain-aegisbank-ai.hf.space/api/:path*`. Commit and push to GitHub.
2. Vercel → **Add New → Project** → import the GitHub repo.
3. Settings: **Root Directory = `frontend`**, Framework Preset **Vite**, Build Command `npm run build`, Output Directory `dist`. **No environment variables needed.**
4. **Deploy.** Open the `*.vercel.app` URL → log in. (CLI alternative: `cd frontend && npx vercel --prod`.)

How it works: the browser calls `/api/v1/...` on the Vercel domain; `vercel.json` rewrites that to your Space, so there is no CORS problem and the JWT never leaves your domains.
*Alternative without rewrites:* set `VITE_API_URL=https://<space>.hf.space/api/v1` in Vercel and add the Space secret `CORS_ORIGINS=["https://<project>.vercel.app"]`.

## 5. Verify (smoke checklist)
- [ ] `…/api/v1/health` returns `{"status":"ok"}`
- [ ] Login as `analyst01`; Dashboard shows data
- [ ] **Transaction Simulator** → submit a *normal* payment → status COMPLETED; open the customer → balance dropped
- [ ] Submit an *anomalous* one → status **FLAGGED** (held); on **Transactions** click **Release** → COMPLETED
- [ ] Login as `auditor01` → `…/api/v1/ledger/reconcile` shows `"balanced": true`
- [ ] **Assistant** page answers "How does the double-entry ledger work?"

## 6. Troubleshooting
| Symptom | Fix |
|---|---|
| Space log: `Refusing to start: JWT_SECRET…` | add the `JWT_SECRET` secret (≥ 32 chars) → **Restart Space** |
| Build runs out of time / fails on pip | **Factory rebuild** from the Space menu; check Logs for the failing package |
| Space page is blank inside huggingface.co but works on the `.hf.space` URL | make sure `ALLOW_IFRAME=true` is in the Dockerfile (it is by default) |
| Vercel site loads but login says "Cannot reach the API" | the Space is asleep or `vercel.json` host is wrong — open the Space URL directly first |
| 429 "Rate limit exceeded" | login limit is 10/min per client; wait a minute |
| Chatbot answers are plain documentation text | no `GROQ_API_KEY` → deterministic mode (by design) |

## 7. Security reminders for a public demo
Use a non-default `DEMO_PASSWORD`, keep real keys only in Secrets (never in git), and remember all data is synthetic.
