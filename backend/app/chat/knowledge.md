## What AegisBank AI is
AegisBank AI is a demo bank back-office platform that helps fraud analysts investigate suspicious payments. It uses synthetic data only (PKR currency, 8 Pakistani cities) and is not connected to any real bank. A payment is submitted, risk-scored with rules plus machine learning, and either posted to the ledger, held for review, or failed. High-risk payments open a fraud case, six AI agents gather evidence, and a human analyst makes the final decision.

## Architecture
React 18 + TypeScript + Tailwind frontend talks to a FastAPI backend over /api/v1 using JWT bearer tokens. The backend uses SQLAlchemy 2 with PostgreSQL in Docker/Kubernetes and SQLite for local development and the Hugging Face demo. Alembic handles migrations. ChromaDB stores the policy vectors for retrieval, a scikit-learn Isolation Forest provides anomaly scores, and LangGraph orchestrates the agents. Groq is an optional LLM; without it everything still works deterministically.

## Transaction lifecycle and the ledger
Every payment goes through POST /transactions. Steps: (1) idempotency check, so a retried request with the same Idempotency-Key never moves money twice; (2) the customer's account row is locked; (3) the payment is risk-scored; (4) then one of three outcomes. COMPLETED: the money moves using double-entry bookkeeping. FLAGGED: the risk was HIGH or CRITICAL, so the funds are held and nothing moves until an analyst releases or declines it. FAILED: for example insufficient funds, the attempt is recorded but no money moves. Everything happens inside one database transaction, so it either fully commits or fully rolls back.

## Double-entry ledger
Each posted payment writes one DEBIT and one CREDIT of the same amount into the append-only ledger_entries table. Transfers to another customer account of the bank credit that account. Money going to merchants, cash or other banks is booked against a system CLEARING account, so total debits always equal total credits. Amounts use Decimal with 2 places, never floats. A customer account can never go below zero. The reconcile endpoint (GET /ledger/reconcile, auditors and admins) proves total debits equal total credits and that each balance equals opening balance plus credits minus debits.

## Held transactions: release and decline
When a payment is FLAGGED the money has not moved. An analyst can POST /transactions/{id}/release, which re-checks the balance under a lock and then posts the ledger entries, or POST /transactions/{id}/decline, which marks it DECLINED. Both actions are written to the audit log. There is nothing to reverse because funds never left the account.

## Risk engine
The rule engine has 7 weighted factors: new device 20, new location 20, unusual amount (more than 5 times the customer average) 20, high velocity (3 or more transactions within 15 minutes) 15, new beneficiary 15, unusual merchant category 10, recent failed attempts 10. The rule score is capped at 100. The final score is 0.6 times the rule score plus 0.4 times the ML anomaly score; without a trained model the rule score is used alone. Bands: LOW 0-30, MEDIUM 31-60, HIGH 61-80, CRITICAL 81-100. HIGH and CRITICAL open a fraud case and hold the funds.

## Machine learning model
An Isolation Forest (scikit-learn, 200 trees, contamination 0.03) is trained on 7 features: amount, deviation from the customer average, velocity in 15 minutes, hour of day, location novelty, device novelty and daily frequency. Scores are normalised to 0 (normal) through 1 (very anomalous). It is trained on synthetic data, so it demonstrates the pipeline rather than real-world accuracy.

## The six AI agents
The LangGraph pipeline runs in order: fraud_detection, transaction_analysis, customer_risk, investigation, rag_policy, decision. Each agent first produces a deterministic result. If a GROQ_API_KEY is set, an LLM may refine the wording, but the output is schema-validated and discarded if anything is wrong. A CRITICAL case can never be waved through by the LLM. A failing agent does not stop the pipeline. The final recommendation (APPROVE_TRANSACTION, ESCALATE_FOR_REVIEW or BLOCK_AND_INVESTIGATE) is advisory only.

## RAG policy retrieval
Five fictional banking policy documents in rag_documents/ are split into sections, converted into TF-IDF vectors and stored in ChromaDB. The rag_policy agent builds a query from the triggered risk factors and retrieves the top 3 sections, which are cited with document, section and relevance score in the investigation. If the index is missing the agent reports unavailable and the case continues.

## Human in the loop and cases
Case statuses are OPEN, INVESTIGATING, ESCALATED, APPROVED and REJECTED. After the agents run, an analyst records approve, escalate or reject on the AI recommendation. A decision of approve or reject is final. Approving the AI recommendation is separate from releasing the held payment, which is done with the release or decline action.

## Roles and permissions
Four roles: ADMIN can do everything. FRAUD_ANALYST can create transactions, run investigations, decide cases and release or decline held payments. AUDITOR can read everything and view the audit log and ledger reconciliation. VIEWER is read-only. The role is re-read from the database on every request, so a demotion takes effect immediately. Denied actions are written to the audit log.

## Audit log
Every analyst action and every denied access is recorded in the append-only audit_logs table with actor, action, case, previous and new status and details. Examples: TRANSACTION_POSTED, TRANSACTION_HELD, TRANSACTION_RELEASED, TRANSACTION_DECLINED, TRANSACTION_FAILED, INVESTIGATION_RUN, RECOMMENDATION_APPROVED, CASE_ESCALATED, ACCESS_DENIED.

## Security features
Passwords are hashed with bcrypt. Login timing is equalised for unknown usernames. JWT tokens pin the HS256 algorithm. The app refuses to start in production with a weak JWT secret. There are per-IP API rate limits and a stricter login limit, security headers, CORS allow-listing and role-based access control on every write endpoint.

## How to use the app
Log in with a demo account (admin, analyst01, auditor01 or viewer01; the demo password is shown on the login page or in the README). Use RUN FRAUD DEMO to create a synthetic anomalous payment and watch the agents investigate it. Use the Transaction Simulator to submit a normal, suspicious or anomalous payment for a customer. Open Customers to see accounts and balances, Fraud Cases to review cases, Audit Logs for the trail and System Health for service status.

## Deployment
The full stack runs with docker compose (PostgreSQL, Redis, FastAPI, nginx-served React) or on Kubernetes using the manifests in k8s/. The public demo runs as a single container on Hugging Face Spaces (FastAPI serving the built React app, SQLite database) and as a Vercel frontend that proxies /api to the Hugging Face backend.

## Known limitations
All data is synthetic and the ML model is trained on the same synthetic distribution, so accuracy figures are not meaningful for real banking. Rate limiting is in-process rather than shared through Redis. Seeded historical transactions predate the ledger and have no ledger entries. The held-funds model re-checks the balance on release instead of reserving it. This is a portfolio demo, not a production banking system.
