# AegisBank AI — Review: issues found, what was fixed, what is still open

Reviewed: the uploaded `Agilebank_project.zip` (FastAPI + React fraud-investigation platform). Baseline: 88 tests passed on Python 3.12.
After the changes below: **112 tests pass**, frontend `tsc` + `vite build` pass, `ruff` is clean, the Alembic migration upgrades/downgrades on SQLite, and the single-container build was smoke-tested end to end.

## 1. The big gap: there was no real "transaction"

`POST /transactions` only inserted a row and scored it. There were no accounts, no balances and no money movement, so it was a fraud *scorer*, not a banking transaction.

| # | Problem | Status |
|---|---|---|
| 1 | No accounts/balances; nothing was debited or credited | **Fixed** — `accounts` table, opening balance seeded per customer |
| 2 | No double-entry ledger | **Fixed** — append-only `ledger_entries`; each payment = 1 DEBIT + 1 CREDIT; external money goes via a SYSTEM clearing account so debits always equal credits |
| 3 | No overdraft / insufficient-funds check | **Fixed** — customer accounts can never go below 0; failed attempt is stored (status `FAILED`) and feeds the risk engine's FAILED_ATTEMPTS factor |
| 4 | No atomicity / locking: two parallel payments could spend the same money | **Fixed** — one DB transaction; account rows locked `FOR UPDATE` in ascending id order (PostgreSQL) so no double-spend and no deadlock |
| 5 | A retried request could pay twice | **Fixed** — `Idempotency-Key` header + unique index; replay returns the original result (HTTP 200, `replayed: true`); same key with different body → 409 |
| 6 | HIGH/CRITICAL payments were only *labelled* "FLAGGED" — in a real bank the money would already be gone | **Fixed** — they are **held**: no money moves until an analyst calls `/release` (funds re-checked under lock) or `/decline`; both audited |
| 7 | Floats for money | **Fixed in the ledger** — `Decimal`, 2 dp, ROUND_HALF_UP. (`transactions.amount` is still exposed as float in JSON for the UI) |
| 8 | No way to prove the books are right | **Fixed** — `GET /ledger/reconcile` (auditor/admin): total debits == total credits, and every balance == opening + credits − debits |

Known limits of the ledger (be ready to say this): held funds are *re-checked* on release, not *reserved*; the clearing account is a hot row under heavy load; seeded history predates the ledger so it has no entries.

## 2. Security / reliability

| # | Problem | Status |
|---|---|---|
| 9 | Rate limiting uses `request.client.host`. Behind nginx/HF/Vercel every user shares the proxy's IP → one global bucket (10 logins/min for *everyone* = easy lockout DoS) | **Fixed** for compose + Hugging Face via `FORWARDED_ALLOW_IPS`. Don't trust `*` if the backend port is publicly reachable (compose publishes 8000 — remove that mapping in production) |
| 10 | Demo accounts incl. `admin` / `AegisDemo123!` are seeded everywhere, also with `ENVIRONMENT=production` | **Mitigated** — password is now overridable with `DEMO_PASSWORD`; still open: don't seed `admin` in production |
| 11 | JWT stored in `sessionStorage` (readable by any XSS), 8 h lifetime, no revocation/refresh | Open — use an HttpOnly cookie + short-lived token |
| 12 | `/api/docs` is public in production | Open — `docs_url=None` when `ENVIRONMENT=production` |
| 13 | Rate limiter is in-process, so it breaks with >1 worker/replica. Redis is deployed in compose/k8s but nothing uses it | Open — move the limiter to Redis or remove Redis from the stack |
| 14 | Any logged-in VIEWER can list every customer's transactions and full beneficiary account numbers (no masking) | Open — mask PII for VIEWER |
| 15 | `FRAUD_ANALYST` can *create* payments and also *release* them (no four-eyes) | Open — separate roles, and require releaser ≠ creator |
| 16 | `X-Frame-Options: DENY` would blank the Hugging Face page (Spaces embed apps in an iframe) | **Fixed** — `ALLOW_IFRAME=true` only in the HF image |

## 3. Data science / AI honesty (interviewers will probe this)

| # | Problem | Status |
|---|---|---|
| 17 | Isolation Forest is trained on the same synthetic data it then scores; no precision/recall/ROC anywhere | Open — the generator knows which rows it made "anomalous": use that as labels, time-split, report metrics |
| 18 | `risk_engine.evaluate` / `features` use *all* of a customer's other transactions, including ones that happen **after** the one being scored (look-ahead leakage when re-analysing old rows) | Open — filter history to `occurred_at < txn.occurred_at` |
| 19 | The six "agents" are mostly deterministic functions; the LLM only rewords them and LangGraph is a straight chain (no branching/tools) | Not a bug — but describe it accurately: *"deterministic core, optional LLM refinement, schema-validated, human decides"* |
| 20 | RAG is TF-IDF over 5 small docs (no semantic embeddings) | Fine for a demo; say so |

## 4. Repo / engineering hygiene

| # | Problem | Status |
|---|---|---|
| 21 | README advertises CI/CD, Trivy, CodeQL, gitleaks, pip-audit — but there was **no `.github/` folder** | **Partly fixed** — added `.github/workflows/ci.yml` (ruff + pytest + frontend build). Add Trivy/CodeQL/gitleaks, or delete those badges. Never claim what the repo does not contain |
| 22 | The zip contained `backend/venv` (Windows, ~4 M lines), `__pycache__`, `.db`, `.git` | **Fixed** in the delivered zip; `.gitignore` artifact patterns corrected (they were anchored to the wrong folder) |
| 23 | `requirements.txt` is a raw `pip freeze` (120 pins) incl. pytest, ruff, build, kubernetes | Open — split `requirements.txt` / `requirements-dev.txt` |
| 24 | Alembic *and* `Base.metadata.create_all` both create tables → schema drift risk | Open — keep Alembic only |
| 25 | `SEED_ON_START` defaults to `true`, so production boots with 10 k fake transactions | Open — default `false` outside demos |
| 26 | Developed on Python 3.14, image is 3.12 | Checked: requirements install and all tests pass on 3.12 |
| 27 | System Health card always says "PostgreSQL" even on SQLite | Nit |

## 5. What was added

* **Ledger + payments service** — `app/services/ledger.py`, `app/services/payments.py`, migration `a1f4d2e7b9c0`, endpoints `/accounts`, `/accounts/{id}/ledger`, `/transactions/{id}/release|decline`, `/ledger/reconcile`.
* **Assistant (chatbot)** — `app/chat/` + `/assistant/chat`. Grounded in `knowledge.md` (TF-IDF retrieval) plus *live* counts from the database. With `GROQ_API_KEY` it answers in English/Urdu/Roman Urdu via the LLM; without a key it returns the best-matching documentation. It has **no tools** (cannot move money or change data), is per-user rate-limited and validates history roles. UI: **Assistant** page in the sidebar.
* **UI** — transaction status column, Release/Decline buttons for held payments, accounts card on the customer page, Idempotency-Key on every submit.
* **Deployment** — `deploy/huggingface/*`, `frontend/vercel.json`, `docs/DEPLOYMENT_GUIDE.md`, CI workflow.

## 6. Interview cheat-sheet (junior role)

*"Walk me through a payment."* Idempotency check → lock account → score (rules 60 % + Isolation Forest 40 %) → hold / fail / post double-entry → audit log → all in one DB transaction.
*"What if the request is retried?"* Idempotency-Key. *"Two payments at once?"* Row lock, ordered by id. *"How do you know the books are right?"* Reconcile endpoint + tests that tamper a balance and expect detection.
*"What would you improve?"* Items 11, 15, 17, 18, 13 above — naming your own gaps shows judgement.
