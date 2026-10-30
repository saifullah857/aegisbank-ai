<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!--                          AegisBank AI  ·  README                           -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f172a,50:1d4ed8,100:06b6d4&height=240&section=header&text=AegisBank%20AI&fontSize=70&fontColor=ffffff&animation=fadeIn&fontAlignY=36&desc=Intelligent%20Fraud%20Investigation%20for%20Modern%20Banking&descSize=20&descAlignY=58" alt="AegisBank AI banner" width="100%"/>

<a href="https://github.com/YOUR_USERNAME/aegisbank-ai">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=2800&pause=900&color=22D3EE&center=true&vCenter=true&multiline=false&width=820&lines=%F0%9F%9B%A1%EF%B8%8F+Explainable+Risk+Scoring+%E2%80%94+Rules+%2B+Machine+Learning;%F0%9F%A4%96+Six-Agent+LangGraph+Investigation+Pipeline;%F0%9F%93%9A+RAG+over+Banking+Policy+with+Cited+Evidence;%F0%9F%91%A9%E2%80%8D%F0%9F%92%BC+Human-in-the-Loop+Decisions+%E2%80%A2+Full+Audit+Trail;%E2%98%B8%EF%B8%8F+Docker+%E2%80%A2+Kubernetes+%E2%80%A2+CI%2FCD+Ready" alt="Typing animation" />
</a>

<br/>

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React_18-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL_16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)

![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)

<br/>

**[🚀 Quick Start](#-quick-start)** &nbsp;•&nbsp;
**[🎯 The Problem](#-the-problem--our-solution)** &nbsp;•&nbsp;
**[🏗️ Architecture](#%EF%B8%8F-architecture)** &nbsp;•&nbsp;
**[🧰 Tech Stack](#-tech-stack)** &nbsp;•&nbsp;
**[🎬 Demo](#-live-demo-in-30-seconds)** &nbsp;•&nbsp;
**[🔐 Security](#-security-by-design)**

</div>

<br/>

> [!NOTE]
> 🇵🇰 **All data in this project is 100% synthetic** (PKR currency, 8 Pakistani cities). The branding is original and the project is **not affiliated with any real bank**.

---

## ✨ At a Glance

<div align="center">

| 🛡️ **7** | 🤖 **6** | 📚 **5** | 👥 **4** | 🧪 **80+** | 🗂️ **15** |
|:---:|:---:|:---:|:---:|:---:|:---:|
| Weighted risk factors | AI agents in the pipeline | Policy documents (RAG) | RBAC roles | Automated tests | Frontend pages |

</div>

---

## 🎯 The Problem → Our Solution

<table>
<tr>
<td width="50%" valign="top">

### 😩 The Problem

Fraud analysts at banks face a painful reality:

- 🌊 **Alert fatigue**: thousands of alerts, most are noise
- 🕳️ **Black-box scores**: nobody can explain *why* a transaction was flagged
- 📖 **Scattered policies**: analysts hunt through documents manually
- ⏱️ **Slow investigations**: gathering context takes longer than deciding
- ⚖️ **Compliance pressure**: every decision must be justified and traceable
- 🤖 **AI distrust**: auto-freezing accounts on a model's guess is dangerous

</td>
<td width="50%" valign="top">

### 💡 The Solution

AegisBank AI turns noise into **explained, evidence-backed cases**:

- ⚖️ **Hybrid scoring**: explainable rules (60%) + Isolation Forest ML (40%)
- 🧾 **Every factor explains itself**: no black box
- 📚 **RAG retrieves the exact policy section** with citations
- 🤖 **Six agents** gather evidence automatically
- 👩‍💼 **Human always decides**: approve / escalate / reject
- 🔒 **Nothing is auto-frozen or reversed**, and every action is audit-logged

</td>
</tr>
</table>

### 🔄 How a Transaction Becomes a Decision

```mermaid
flowchart LR
    T([💳 Transaction]) --> R[⚖️ Rule Engine<br/>7 weighted factors]
    R --> M[🌲 Isolation Forest<br/>anomaly score]
    M --> S{🎚️ Combined Score<br/>0.6·rules + 0.4·ML}
    S -->|LOW / MEDIUM| OK([✅ Monitor])
    S -->|HIGH / CRITICAL| C[📂 Case Opened]
    C --> A1[🕵️ Fraud Detection] --> A2[📊 Transaction Analysis] --> A3[👤 Customer Risk]
    A3 --> A4[🔎 Investigation] --> A5[📚 RAG Policy] --> A6[🎯 Decision]
    A6 --> H{{👩‍💼 Human Analyst}}
    H -->|approve / escalate / reject| L[(🧾 Audit Log)]

    style T fill:#1d4ed8,color:#fff,stroke:#0f172a
    style S fill:#7c3aed,color:#fff,stroke:#0f172a
    style C fill:#dc2626,color:#fff,stroke:#0f172a
    style H fill:#059669,color:#fff,stroke:#0f172a
    style L fill:#0891b2,color:#fff,stroke:#0f172a
    style OK fill:#16a34a,color:#fff,stroke:#0f172a
```

---

## 🌟 Key Features

<table>
<tr>
<td align="center" width="25%">
<h3>⚖️</h3>
<b>Explainable Risk Engine</b><br/>
<sub>7 weighted factors computed from real data. Each one explains its own contribution.</sub>
</td>
<td align="center" width="25%">
<h3>🌲</h3>
<b>ML Anomaly Detection</b><br/>
<sub>Isolation Forest on amount, velocity, hour, location & device novelty.</sub>
</td>
<td align="center" width="25%">
<h3>🤖</h3>
<b>Multi-Agent Pipeline</b><br/>
<sub>Six LangGraph agents return structured findings and evidence only.</sub>
</td>
<td align="center" width="25%">
<h3>📚</h3>
<b>RAG with Citations</b><br/>
<sub>Policy retrieval backed by ChromaDB, with document, section & score.</sub>
</td>
</tr>
<tr>
<td align="center">
<h3>👩‍💼</h3>
<b>Human-in-the-Loop</b><br/>
<sub>Approve, escalate or reject with confirmation. Never automatic.</sub>
</td>
<td align="center">
<h3>🧾</h3>
<b>Immutable Audit Trail</b><br/>
<sub>Every action, and every denied action, is logged for auditors.</sub>
</td>
<td align="center">
<h3>🛟</h3>
<b>Graceful Fallback</b><br/>
<sub>No LLM key? Deterministic analysis still runs end to end.</sub>
</td>
<td align="center">
<h3>🎮</h3>
<b>Transaction Simulator</b><br/>
<sub>Generate fresh anomalous transactions and watch the pipeline react.</sub>
</td>
</tr>
</table>

---

## 🏗️ Architecture

```mermaid
flowchart TB
    subgraph CLIENT["🖥️ Presentation Layer"]
        UI["React 18 + TypeScript<br/>Tailwind CSS + Recharts"]
    end

    subgraph SERVER["⚙️ Application Layer"]
        API["⚡ FastAPI<br/>JWT • RBAC • Rate Limits"]
        RISK["⚖️ Risk Engine"]
        ORCH["🧠 LangGraph Orchestrator<br/>6 agents"]
        RAG["📚 RAG Service"]
    end

    subgraph DATA["🗄️ Data & Intelligence Layer"]
        PG[("🐘 PostgreSQL")]
        CH[("🔮 ChromaDB<br/>policy index")]
        ML["🌲 Isolation Forest<br/>.joblib model"]
        RD[("⚡ Redis")]
    end

    LLM["☁️ Groq LLM<br/>(optional)"]

    UI -- "/api + JWT" --> API
    API --> RISK
    API --> ORCH
    RISK --> ML
    ORCH --> RAG
    RAG --> CH
    API --> PG
    API -. health .-> RD
    ORCH -. optional refine .-> LLM

    style CLIENT fill:#0f172a,stroke:#22d3ee,color:#fff
    style SERVER fill:#1e1b4b,stroke:#818cf8,color:#fff
    style DATA fill:#052e16,stroke:#4ade80,color:#fff
    style LLM fill:#7c2d12,stroke:#fb923c,color:#fff
```

<details>
<summary><b>⚖️ &nbsp;Risk Engine: the 7 weighted factors</b> (click to expand)</summary>

<br/>

| # | Factor | Weight | Trigger | Visual |
|:-:|:--|:-:|:--|:--|
| 1 | 📱 New device | **20** | Device never seen for this customer | `████████████████████` |
| 2 | 📍 New location | **20** | City/location outside customer history | `████████████████████` |
| 3 | 💰 Unusual amount | **20** | Amount greater than 5× customer average | `████████████████████` |
| 4 | ⚡ Velocity | **15** | 3 or more transactions within ±15 minutes | `███████████████░░░░░` |
| 5 | 👤 New beneficiary | **15** | First-time payee | `███████████████░░░░░` |
| 6 | 🏪 Unusual merchant | **10** | Merchant category outside normal pattern | `██████████░░░░░░░░░░` |
| 7 | ❌ Failed attempts | **10** | Recent failed authentication attempts | `██████████░░░░░░░░░░` |

**Risk bands**

| Score | Level | Action |
|:-:|:-:|:--|
| 🟢 0 – 30 | **LOW** | Monitor |
| 🟡 31 – 60 | **MEDIUM** | Monitor, keep on watch |
| 🟠 61 – 80 | **HIGH** | Case opened, agents run |
| 🔴 81 – 100 | **CRITICAL** | Case opened, agents run, priority review |

**Final score** = `0.6 × rule score + 0.4 × ML anomaly score`. If no model is loaded, the rule engine works on its own.

</details>

<details>
<summary><b>🤖 &nbsp;The Six Agents</b> (click to expand)</summary>

<br/>

| Step | Agent | Responsibility |
|:-:|:--|:--|
| 1️⃣ | 🕵️ **Fraud Detection** | Summarises the score and the factors that fired |
| 2️⃣ | 📊 **Transaction Analysis** | Compares the transaction against the customer's normal behaviour |
| 3️⃣ | 👤 **Customer Risk** | Assesses the customer's overall risk profile |
| 4️⃣ | 🔎 **Investigation** | Collects and organises the evidence |
| 5️⃣ | 📚 **RAG Policy** | Retrieves relevant policy sections with citations |
| 6️⃣ | 🎯 **Decision** | Recommends an action for the human analyst |

> [!IMPORTANT]
> Agents return **structured findings and evidence only**, never reasoning traces. Deterministic logic runs first. If a `GROQ_API_KEY` is set, wording may be LLM-refined, but the output is schema-validated and **discarded on any problem**. A CRITICAL case can never be waved through, and a failing agent never stops the pipeline.

</details>

<details>
<summary><b>📚 &nbsp;RAG Knowledge Base</b> (click to expand)</summary>

<br/>

Five fictional banking policies live in `rag_documents/`:

- 🪪 `customer_verification_policy.md`
- 💳 `card_fraud_investigation_policy.md`
- 🔐 `account_security_policy.md`
- 🚨 `suspicious_activity_escalation_policy.md`
- 📈 `transaction_monitoring_policy.md`

**Pipeline:** `Markdown` → `section chunks` → `TF-IDF vectors` → `ChromaDB` → `cited retrieval` *(document, section, content, score)*.

If the index is unavailable, the agent reports "unavailable" and the case continues using rule evidence.

</details>

---

## 🧰 Tech Stack

<div align="center">

<img src="https://skillicons.dev/icons?i=python,fastapi,react,ts,tailwind,vite,postgres,redis,docker,kubernetes,githubactions,nginx,sqlite&perline=13" alt="Tech stack icons"/>

</div>

<br/>

| Layer | Technologies |
|:--|:--|
| 🎨 **Frontend** | ![React](https://img.shields.io/badge/React_18-61DAFB?logo=react&logoColor=black) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white) ![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white) ![Tailwind](https://img.shields.io/badge/Tailwind-06B6D4?logo=tailwindcss&logoColor=white) ![Recharts](https://img.shields.io/badge/Recharts-22b5bf) ![React Router](https://img.shields.io/badge/React_Router-CA4245?logo=reactrouter&logoColor=white) ![Axios](https://img.shields.io/badge/Axios-5A29E4?logo=axios&logoColor=white) |
| ⚙️ **Backend** | ![Python](https://img.shields.io/badge/Python_3.12-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white) ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy_2-D71F00?logo=sqlalchemy&logoColor=white) ![Alembic](https://img.shields.io/badge/Alembic-migrations-6BA81E) ![Pydantic](https://img.shields.io/badge/Pydantic_v2-E92063?logo=pydantic&logoColor=white) ![Uvicorn](https://img.shields.io/badge/Uvicorn-499848) |
| 🧠 **AI / ML** | ![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?logo=langchain&logoColor=white) ![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?logo=scikitlearn&logoColor=white) ![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6446) ![Groq](https://img.shields.io/badge/Groq_LLM-F55036) ![NumPy](https://img.shields.io/badge/NumPy-013243?logo=numpy&logoColor=white) ![joblib](https://img.shields.io/badge/joblib-model_store-lightgrey) |
| 🗄️ **Data** | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL_16-4169E1?logo=postgresql&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite_(dev)-003B57?logo=sqlite&logoColor=white) ![Redis](https://img.shields.io/badge/Redis_7-DC382D?logo=redis&logoColor=white) |
| 🔐 **Security** | ![JWT](https://img.shields.io/badge/JWT_HS256-000000?logo=jsonwebtokens&logoColor=white) ![bcrypt](https://img.shields.io/badge/bcrypt-hashing-blueviolet) ![RBAC](https://img.shields.io/badge/RBAC-4_roles-success) ![Rate Limit](https://img.shields.io/badge/Rate_Limiting-active-orange) |
| 🚢 **DevOps** | ![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white) ![Compose](https://img.shields.io/badge/Docker_Compose-2496ED?logo=docker&logoColor=white) ![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?logo=kubernetes&logoColor=white) ![Nginx](https://img.shields.io/badge/Nginx-009639?logo=nginx&logoColor=white) ![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white) |
| 🛡️ **Quality & Security Scanning** | ![pytest](https://img.shields.io/badge/pytest-0A9EDC?logo=pytest&logoColor=white) ![Ruff](https://img.shields.io/badge/Ruff-D7FF64?logo=ruff&logoColor=black) ![Trivy](https://img.shields.io/badge/Trivy-1904DA?logo=aquasecurity&logoColor=white) ![CodeQL](https://img.shields.io/badge/CodeQL-2B7489?logo=github&logoColor=white) ![Gitleaks](https://img.shields.io/badge/Gitleaks-secret_scan-red) ![pip-audit](https://img.shields.io/badge/pip--audit-deps-blue) |

---

## 🔐 Security by Design

<table>
<tr>
<td width="33%" valign="top">

#### 🔑 Authentication
- JWT with **HS256 pinned**
- Passwords hashed with **bcrypt**
- Production **refuses weak** `JWT_SECRET`
- Login **rate limiting**

</td>
<td width="33%" valign="top">

#### 🛂 Authorisation
- **RBAC re-read from DB** on every request
- Access denials are **audit-logged**
- Least-privilege roles
- No keys in the frontend

</td>
<td width="33%" valign="top">

#### 🧱 Hardening
- Secure HTTP headers
- **CORS allow-list**
- Pydantic input validation
- **ORM-only SQL** (no raw queries)

</td>
</tr>
</table>

### 👥 Role Matrix

| Capability | 👑 ADMIN | 🕵️ FRAUD_ANALYST | 📋 AUDITOR | 👁️ VIEWER |
|:--|:-:|:-:|:-:|:-:|
| View dashboards, cases & customers | ✅ | ✅ | ✅ | ✅ |
| Investigate cases | ✅ | ✅ | ❌ | ❌ |
| Approve / Escalate / Reject | ✅ | ✅ | ❌ | ❌ |
| Read audit logs | ✅ | ❌ | ✅ | ❌ |
| Full administration | ✅ | ❌ | ❌ | ❌ |

---

## 🚀 Quick Start

### 🐳 Option 1: Docker (recommended, everything in one command)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/aegisbank-ai.git
cd aegisbank-ai

# 2. Create your environment file
cp .env.example .env
#    ➜ set POSTGRES_PASSWORD and JWT_SECRET
#    ➜ generate a strong secret with:
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 3. Launch the whole platform
docker compose up --build
```

| 🌐 Service | 🔗 URL |
|:--|:--|
| Web application | http://localhost:8080 |
| API documentation (Swagger) | http://localhost:8000/api/docs |

> [!TIP]
> On first start the platform automatically **migrates the database, seeds 1,000 customers and ~10k transactions, trains the ML model and indexes the policies**. This takes about 1 to 2 minutes.

### 🔑 Demo Accounts

*(synthetic, password for all: `AegisDemo123!`)*

| Username | Role | Best for |
|:--|:--|:--|
| `analyst01` | 🕵️ Fraud Analyst | Running the demo and making decisions |
| `auditor01` | 📋 Auditor | Reviewing the audit trail |
| `viewer01` | 👁️ Viewer | Read-only exploration |
| `admin` | 👑 Admin | Full access |

<details>
<summary><b>💻 &nbsp;Option 2: Local development</b> (click to expand)</summary>

<br/>

```bash
# ── Backend ──────────────────────────────────────────────
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

export JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")

./venv/bin/alembic upgrade head             # create schema
./venv/bin/python -m app.db.seed            # seed synthetic data + train model
./venv/bin/python -m app.rag.policy_service # index policies into ChromaDB
./venv/bin/uvicorn app.main:app --reload    # SQLite by default

# ── Frontend (new terminal) ──────────────────────────────
cd frontend
npm install
npm run dev                                 # http://localhost:5173
```

Use `DATABASE_URL` to switch to PostgreSQL. The Vite dev server proxies `/api` to port 8000.

</details>

<details>
<summary><b>☸️ &nbsp;Option 3: Kubernetes</b> (click to expand)</summary>

<br/>

```bash
kubectl apply -f k8s/namespace.yaml -f k8s/configmap.yaml

kubectl -n aegisbank create secret generic aegis-secrets \
  --from-literal=POSTGRES_PASSWORD=... \
  --from-literal=JWT_SECRET=... \
  --from-literal=DATABASE_URL=postgresql+psycopg2://aegis:...@postgres:5432/aegisbank \
  --from-literal=GROQ_API_KEY=

kubectl apply -f k8s/postgres-service.yaml -f k8s/postgres-statefulset.yaml \
              -f k8s/redis-service.yaml    -f k8s/redis-deployment.yaml

kubectl apply -f k8s/backend-init-job.yaml   # migrations + seed (run once)

kubectl apply -f k8s/backend-deployment.yaml -f k8s/backend-service.yaml \
              -f k8s/frontend-deployment.yaml -f k8s/frontend-service.yaml \
              -f k8s/ingress.yaml
```

- Replace the `ghcr.io/your-org/...` image names with your own.
- `secrets.yaml` is a **placeholder template**. Never commit real values.
- Backend runs **2 replicas** with rolling updates (`maxUnavailable: 0`), resource requests/limits, and startup, readiness and liveness probes.

</details>

<details>
<summary><b>⚙️ &nbsp;Environment variables</b> (click to expand)</summary>

<br/>

| Variable | Required | Description |
|:--|:-:|:--|
| `POSTGRES_PASSWORD` | ✅ | Database password |
| `JWT_SECRET` | ✅ | At least 32 characters |
| `ENVIRONMENT` | ➖ | `production` enforces strict checks; `development` relaxes them |
| `DATABASE_URL` | ➖ | SQLAlchemy URL (SQLite by default locally) |
| `GROQ_API_KEY` | ➖ | Optional. Leave empty to use the deterministic fallback |
| `GROQ_MODEL` | ➖ | Default `llama-3.3-70b-versatile` |
| `REDIS_URL` | ➖ | Redis connection for health checks |
| `CORS_ORIGINS` | ➖ | Allowed frontend origins |
| `CHROMA_PERSIST_DIR` | ➖ | ChromaDB storage directory |
| `ML_MODEL_PATH` | ➖ | Path to the Isolation Forest `.joblib` |
| `RAG_EMBEDDER_PATH` | ➖ | Path to the TF-IDF embedder |
| `API_RATE_LIMIT_PER_MINUTE` | ➖ | Global rate limit |
| `LOGIN_RATE_LIMIT_PER_MINUTE` | ➖ | Login rate limit |
| `SEED_ON_START` | ➖ | Seed synthetic data on first start |

</details>

---

## 🎬 Live Demo in 30 Seconds

```mermaid
sequenceDiagram
    autonumber
    actor A as 🕵️ analyst01
    participant UI as 🖥️ Dashboard
    participant API as ⚡ FastAPI
    participant AG as 🤖 6 Agents
    participant R as 📚 RAG
    actor U as 📋 auditor01

    A->>UI: Click "▶ RUN FRAUD DEMO"
    UI->>API: POST /demo/transaction
    API->>API: Create anomalous txn & score (rules + ML)
    API->>AG: Open case, run pipeline
    AG->>R: Retrieve policy sections
    R-->>AG: Cited policy evidence
    AG-->>UI: Recommendation + evidence timeline
    A->>UI: Approve / Escalate / Reject (confirm)
    UI->>API: POST /investigations/{case}/decision
    API-->>U: Everything appears in the Audit Log
```

1. 🔐 Log in as **`analyst01`** and click **▶ RUN FRAUD DEMO**
2. 👀 Watch the transaction get scored, the six agents run and policies get cited
3. ✅ Make a decision: **Approve / Escalate / Reject** (with confirmation)
4. 📋 Log in as **`auditor01`** and open **Audit Logs** to see every action recorded

**Also explore:** 📊 Dashboard · 📂 Fraud Cases & Timeline · 🎮 Transaction Simulator · 📈 Analytics · 📚 Policies & RAG · 🩺 System Health

---

## 🗺️ Application Pages

| Page | Purpose |
|:--|:--|
| 📊 **Dashboard** | Live KPIs and risk overview |
| 📂 **Fraud Cases / Case Detail** | Case list, timeline, agent findings, citations, decision panel |
| 👥 **Customers / Customer Detail** | Customer profiles and risk history |
| 💳 **Transactions** | Searchable transaction ledger |
| 🔎 **Investigations** | Open and closed investigations |
| 🤖 **Agents** | Agent pipeline status and outputs |
| 📈 **Analytics** | Charts and fraud trends |
| 📚 **Policies** | Browse and search the RAG knowledge base |
| 🧾 **Audit Logs** | Complete action history (Auditor / Admin) |
| 🩺 **System Health** | Database, Redis, model and index status |
| 🎮 **Simulator** | Generate synthetic transactions |
| ⚙️ **Settings** | User and system preferences |

---

## 🔌 API Reference

> Interactive Swagger docs at **`/api/docs`**

| Method | Endpoint | Description |
|:-:|:--|:--|
| ![POST](https://img.shields.io/badge/POST-f59e0b?style=flat-square) | `/auth/login` | Authenticate and receive a JWT |
| ![GET](https://img.shields.io/badge/GET-22c55e?style=flat-square) | `/dashboard/stats` · `/dashboard/analytics` | Dashboard metrics |
| ![GET](https://img.shields.io/badge/GET-22c55e?style=flat-square) | `/customers` · `/customers/{id}` | Customer data |
| ![GET](https://img.shields.io/badge/GET-22c55e?style=flat-square) ![POST](https://img.shields.io/badge/POST-f59e0b?style=flat-square) | `/transactions` | List or create transactions |
| ![POST](https://img.shields.io/badge/POST-f59e0b?style=flat-square) | `/fraud/analyze` | Score a transaction |
| ![GET](https://img.shields.io/badge/GET-22c55e?style=flat-square) | `/fraud/cases` · `/fraud/cases/{ref}` · `/fraud/cases/{ref}/timeline` | Fraud cases |
| ![GET](https://img.shields.io/badge/GET-22c55e?style=flat-square) | `/investigations/{case}` | Investigation details |
| ![POST](https://img.shields.io/badge/POST-f59e0b?style=flat-square) | `/investigations/{case}/approve` · `/escalate` · `/reject` | Human decision |
| ![GET](https://img.shields.io/badge/GET-22c55e?style=flat-square) | `/agents` · `/policies` · `/policies/search` · `/policies/{slug}` · `/audit` | Agents, RAG and audit |
| ![POST](https://img.shields.io/badge/POST-f59e0b?style=flat-square) | `/simulator/generate` · `/demo/transaction` | Simulation and demo |
| ![GET](https://img.shields.io/badge/GET-22c55e?style=flat-square) | `/health` · `/health/ready` · `/system/health` | Health probes |

---

## 🔄 CI/CD Pipeline

```mermaid
flowchart LR
    subgraph CI["🧪 ci.yml"]
        direction LR
        L[Lint] --> U[Unit Tests] --> I[PostgreSQL<br/>Integration] --> F[Frontend<br/>Build] --> D[Docker<br/>Build] --> T[Trivy Scan]
    end
    subgraph SEC["🛡️ security.yml"]
        direction LR
        G[Gitleaks] --- P[pip-audit] --- N[npm audit] --- TF[Trivy fs/IaC] --- CQ[CodeQL]
    end
    subgraph CD["🚢 cd.yml (main)"]
        direction LR
        T2[Tests] --> PU[Push Images] --> MJ[Migrate Job] --> RO[Rollout] --> HC[Health Check]
    end
    CI --> CD
    SEC --> CD

    style CI fill:#0c4a6e,stroke:#38bdf8,color:#fff
    style SEC fill:#7f1d1d,stroke:#f87171,color:#fff
    style CD fill:#14532d,stroke:#4ade80,color:#fff
```

<details>
<summary><b>🔑 &nbsp;Required GitHub Secrets</b></summary>

<br/>

`GROQ_API_KEY` · `DATABASE_URL` · `JWT_SECRET` · `POSTGRES_PASSWORD` · `REGISTRY_USERNAME` · `REGISTRY_PASSWORD` · `KUBE_CONFIG` *(base64)*

</details>

---

## 🧪 Testing

```bash
# Backend: unit + integration (auth/JWT, RBAC, risk engine, ML, agents, RAG, API, audit, fallback)
cd backend && ./venv/bin/python -m pytest

# End-to-end smoke test against a running API
API_URL=http://localhost:8000/api/v1 ./venv/bin/python scripts/smoke_test.py

# Frontend: type-check + production build
cd frontend && npm run lint && npm run build
```

| ✅ Covered Area | |
|:--|:--|
| 🔐 Authentication & JWT | 🛂 Role-based access control |
| ⚖️ Risk engine & scoring | 🌲 ML inference |
| 🤖 Agent pipeline & fallback | 📚 RAG retrieval |
| 🌐 REST API | 🧾 Audit logging |

---

## 📁 Project Structure

```text
aegisbank-ai/
├── 🐍 backend/
│   ├── app/
│   │   ├── api/          # REST endpoints (cases, insights, extras)
│   │   ├── core/         # config, security, RBAC deps, metrics
│   │   ├── db/           # models, session, seed, synthetic data
│   │   ├── ml/           # features, training, Isolation Forest inference
│   │   ├── rag/          # chunking + ChromaDB policy service
│   │   ├── services/     # risk engine, scoring, agents, LLM client
│   │   └── main.py       # FastAPI application
│   ├── alembic/          # database migrations
│   ├── tests/            # pytest suite
│   └── scripts/          # start.sh, smoke_test.py
├── ⚛️ frontend/
│   └── src/
│       ├── pages/        # Dashboard, Cases, Simulator, Audit, ...
│       ├── components/   # charts, AgentPipeline, DecisionPanel, Timeline
│       ├── layouts/      # AppLayout
│       ├── hooks/        # useAuth, useAsync
│       └── services/     # API client
├── 📚 rag_documents/     # 5 banking policy documents
├── ☸️ k8s/               # Kubernetes manifests
├── 🔄 .github/workflows/ # ci.yml · cd.yml · security.yml
├── 🐳 docker-compose.yml
└── 🔧 .env.example
```

---

## 🔮 Roadmap

- [ ] 🧬 Real embeddings (sentence-transformers) instead of TF-IDF
- [ ] ⚡ Redis-backed shared rate limits and caching
- [ ] 🔑 Refresh tokens and SSO
- [ ] 📡 Streaming agent progress via SSE
- [ ] 📉 Model drift monitoring and a retraining pipeline
- [ ] ⛵ Helm chart / Kustomize overlays
- [ ] 🎭 Automated browser (Playwright) UI tests

---

## 🤝 Contributing

Contributions, issues and feature requests are welcome!

1. 🍴 Fork the project
2. 🌿 Create a feature branch: `git checkout -b feature/amazing-feature`
3. 💾 Commit your changes: `git commit -m "Add amazing feature"`
4. 📤 Push to the branch: `git push origin feature/amazing-feature`
5. 🔃 Open a Pull Request

---

## 👨‍💻 Author

<div align="center">

**Your Name**

[![GitHub](https://img.shields.io/badge/GitHub-YOUR_USERNAME-181717?style=for-the-badge&logo=github)](https://github.com/YOUR_USERNAME)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin)](https://linkedin.com/in/YOUR_PROFILE)
[![Email](https://img.shields.io/badge/Email-Contact-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:your.email@example.com)

<br/>

⭐ **If you found this project useful, please give it a star!** ⭐

<br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:06b6d4,50:1d4ed8,100:0f172a&height=120&section=footer" alt="footer" width="100%"/>

</div>