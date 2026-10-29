# AegisBank AI — Intelligent Fraud Investigation for Modern Banking

AI-assisted fraud investigation platform for bank analysts: deterministic risk rules + Isolation Forest anomaly
detection + a six-agent LangGraph pipeline + RAG over banking policy + a human-in-the-loop decision and a full audit trail.
**All data is synthetic** (PKR, 8 Pakistani cities). Original branding; not affiliated with any real bank.

## Problem → Solution
Analysts drown in alerts and must justify every decision. AegisBank AI scores every transaction (explainable rules 60% +
ML 40%), opens a case for HIGH/CRITICAL, runs six agents that return **structured findings and evidence only** (no
reasoning traces), cites the relevant policy sections, and *recommends* an action. A human approves, escalates or
rejects; nothing is ever frozen or reversed automatically; every action is audit-logged.

```mermaid
flowchart LR
  T[Transaction] --> R[Rule engine] --> M[Isolation Forest] --> A1[Fraud Detection]
  A1 --> A2[Transaction Analysis] --> A3[Customer Risk] --> A4[Investigation] --> A5[RAG Policy] --> A6[Decision]
  A6 --> H[Human analyst] --> L[(Audit log)]
```

## Architecture
```mermaid
flowchart TB
  UI[React + TS + Tailwind + Recharts] -->|/api, JWT| API[FastAPI]
  API --> DB[(PostgreSQL)]
  API --> V[(ChromaDB policy index)]
  API --> ML[Isolation Forest .joblib]
  API --> G[LangGraph orchestrator] -.optional.-> LLM[Groq]
  API -.health.-> Redis[(Redis)]
```
- **Risk engine** (`services/risk_engine.py`): 7 weighted factors computed from real data — new device 20, new location 20,
  unusual amount 20 (>5× customer average), velocity 15 (≥3 in ±15 min), new beneficiary 15, unusual merchant 10, failed attempts 10.
  0–30 LOW, 31–60 MEDIUM, 61–80 HIGH, 81–100 CRITICAL. Every factor explains itself.
- **ML** (`app/ml`): Isolation Forest on amount, deviation, velocity, hour, location deviation, device novelty, frequency.
  Combined score = 0.6·rules + 0.4·ML. No model → rule engine alone.
- **Agents** (`services/agents.py`): fraud_detection → transaction_analysis → customer_risk → investigation → rag_policy → decision.
  Deterministic first; if `GROQ_API_KEY` is set the wording may be LLM-refined, schema-validated, and discarded on any problem
  (a CRITICAL case can never be waved through). A failing agent never stops the pipeline.
- **RAG** (`app/rag`, `rag_documents/`): 5 fictional policies → section chunks → TF-IDF vectors in ChromaDB → cited retrieval
  (document, section, content, score). Index missing → agent reports "unavailable" and the case continues on rule evidence.
- **Fallback:** without Groq the UI shows “AI provider unavailable — running deterministic fallback analysis.” Everything works.
- **Security:** JWT (HS256 pinned), bcrypt, RBAC re-read from DB per request, denials audit-logged, login + global rate limits,
  secure headers, CORS allow-list, Pydantic validation, ORM-only SQL, production refuses weak `JWT_SECRET`, no keys in the frontend.

Roles: **ADMIN** all · **FRAUD_ANALYST** investigate/decide · **AUDITOR** read + audit log · **VIEWER** read-only.

## Run it
### Docker (everything)
```bash
cp .env.example .env     # set POSTGRES_PASSWORD and JWT_SECRET (python -c "import secrets;print(secrets.token_urlsafe(48))")
docker compose up --build
```
Open http://localhost:8080 · API docs http://localhost:8000/api/docs. First start migrates, seeds 1,000 customers / ~10k transactions,
trains the model and indexes policies (~1–2 min).
Demo logins (synthetic, password `AegisDemo123!`): `analyst01`, `auditor01`, `viewer01`, `admin`.

### Local development
```bash
cd backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
export JWT_SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
./venv/bin/alembic upgrade head && ./venv/bin/python -m app.db.seed && ./venv/bin/python -m app.rag.policy_service
./venv/bin/uvicorn app.main:app --reload            # SQLite by default; set DATABASE_URL for PostgreSQL
cd ../frontend && npm install && npm run dev        # http://localhost:5173 (proxies /api to :8000)
```
Env vars: `DATABASE_URL`, `JWT_SECRET`, `ENVIRONMENT`, `GROQ_API_KEY` (optional), `GROQ_MODEL`, `REDIS_URL`, `CORS_ORIGINS`,
`CHROMA_PERSIST_DIR`, `ML_MODEL_PATH`, `RAG_EMBEDDER_PATH`, `API_RATE_LIMIT_PER_MINUTE`, `LOGIN_RATE_LIMIT_PER_MINUTE`.

### Kubernetes
```bash
kubectl apply -f k8s/namespace.yaml -f k8s/configmap.yaml
kubectl -n aegisbank create secret generic aegis-secrets --from-literal=POSTGRES_PASSWORD=... \
  --from-literal=JWT_SECRET=... --from-literal=DATABASE_URL=postgresql+psycopg2://aegis:...@postgres:5432/aegisbank --from-literal=GROQ_API_KEY=
kubectl apply -f k8s/postgres-service.yaml -f k8s/postgres-statefulset.yaml -f k8s/redis-service.yaml -f k8s/redis-deployment.yaml
kubectl apply -f k8s/backend-init-job.yaml      # migrations + seed, once
kubectl apply -f k8s/backend-deployment.yaml -f k8s/backend-service.yaml -f k8s/frontend-deployment.yaml -f k8s/frontend-service.yaml -f k8s/ingress.yaml
```
Replace `ghcr.io/your-org/...` image names. `secrets.yaml` is a placeholder template — never commit real values.
Backend: 2 replicas, rolling update (maxUnavailable 0), requests/limits, startup/readiness/liveness probes.

### CI/CD (GitHub Actions)
`ci.yml` lint → unit tests → PostgreSQL integration (migrate, seed, API smoke test) → frontend build → Docker build → Trivy.
`security.yml` gitleaks, pip-audit, npm audit, Trivy fs/IaC, CodeQL. `cd.yml` on `main`: tests → push images → secrets from GitHub
→ migrate Job → rollout → health check. Secrets: `GROQ_API_KEY`, `DATABASE_URL`, `JWT_SECRET`, `POSTGRES_PASSWORD`, `REGISTRY_USERNAME`,
`REGISTRY_PASSWORD`, `KUBE_CONFIG` (base64).

## Demo (≈30 s)
Log in as `analyst01` → **▶ RUN FRAUD DEMO**. A fresh synthetic anomalous transaction is created and scored (rules + ML), the six agents run,
policy is retrieved with citations, a recommendation appears, and you Approve / Escalate / Reject (with confirmation). Then log in as
`auditor01` → **Audit Logs**. Also: Dashboard, Fraud Cases → case timeline, Transaction Simulator, Analytics, Policies & RAG, System Health.

## Tests
```bash
cd backend && ./venv/bin/python -m pytest        # 88 tests: auth/JWT, RBAC, risk engine, ML, agents, RAG, API, audit, fallback
API_URL=http://localhost:8000/api/v1 ./venv/bin/python scripts/smoke_test.py   # end-to-end against a running API
cd frontend && npm run lint && npm run build
```

## API (Swagger at `/api/docs`)
`POST /auth/login` · `GET /dashboard/stats|analytics` · `GET /customers[/{id}]` · `GET|POST /transactions` · `POST /fraud/analyze` ·
`GET /fraud/cases[/{ref}[/timeline]]` · `GET /investigations/{case}` · `POST /investigations/{case}/approve|escalate|reject` ·
`GET /agents|policies|policies/search|policies/{slug}|audit` · `POST /simulator/generate` · `POST /demo/transaction` ·
`GET /health|health/ready|system/health`.

## Future improvements
Real embeddings (sentence-transformers) instead of TF-IDF; Redis-backed shared rate limits and caching; refresh tokens/SSO; streaming agent
progress (SSE); model drift monitoring and retraining pipeline; Helm chart / Kustomize overlays; automated browser (Playwright) UI tests.
