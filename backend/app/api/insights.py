"""Read-only insight endpoints: dashboard, analytics, agents registry, policies, system health.
Every figure is aggregated from the database / real checks at request time — nothing is hardcoded."""
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

import psutil
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, case, cast, func, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import current_user
from app.core.metrics import metrics
from app.db.base import AgentExecution, FraudCase, Investigation, Transaction, User
from app.db.session import get_db
from app.rag import policy_service
from app.rag.chunking import load_all
from app.services.agents import AGENT_ORDER, GRAPH

router = APIRouter()
LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
STATUSES = ("OPEN", "INVESTIGATING", "ESCALATED", "APPROVED", "REJECTED")


def _day(col):
    return func.date(col)


@router.get("/dashboard/stats")
def dashboard_stats(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db), _: User = Depends(current_user)):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    by_status = dict(db.query(FraudCase.status, func.count()).group_by(FraudCase.status).all())
    cases_q = db.query(FraudCase).join(Transaction, FraudCase.transaction_id == Transaction.id)
    over_time = (db.query(_day(Transaction.occurred_at), func.count(FraudCase.id)).select_from(FraudCase)
                 .join(Transaction, FraudCase.transaction_id == Transaction.id).filter(Transaction.occurred_at >= cutoff)
                 .group_by(_day(Transaction.occurred_at)).order_by(_day(Transaction.occurred_at)).all())
    trend = (db.query(_day(Transaction.occurred_at), func.count(Transaction.id),
                      func.sum(case((Transaction.risk_level.in_(("MEDIUM", "HIGH", "CRITICAL")), 1), else_=0)))
             .filter(Transaction.occurred_at >= cutoff).group_by(_day(Transaction.occurred_at)).order_by(_day(Transaction.occurred_at)).all())
    dist = dict(db.query(Transaction.risk_level, func.count()).filter(Transaction.risk_level.isnot(None)).group_by(Transaction.risk_level).all())
    by_type = db.query(Transaction.transaction_type, func.count(FraudCase.id)).select_from(FraudCase).join(Transaction, FraudCase.transaction_id == Transaction.id) \
        .group_by(Transaction.transaction_type).order_by(func.count(FraudCase.id).desc()).all()
    by_loc = db.query(Transaction.location, func.count(FraudCase.id)).select_from(FraudCase).join(Transaction, FraudCase.transaction_id == Transaction.id) \
        .group_by(Transaction.location).order_by(func.count(FraudCase.id).desc()).all()
    recent = cases_q.order_by(Transaction.occurred_at.desc()).limit(10).all()
    from app.api.cases import case_out
    return {
        "totals": {"total_transactions": db.query(func.count(Transaction.id)).scalar(),
                   "suspicious_transactions": db.query(func.count(Transaction.id)).filter(Transaction.risk_level.in_(("MEDIUM", "HIGH", "CRITICAL"))).scalar(),
                   "high_risk_cases": db.query(func.count(FraudCase.id)).scalar(),
                   "cases_under_investigation": by_status.get("INVESTIGATING", 0) + by_status.get("ESCALATED", 0),
                   "open_cases": by_status.get("OPEN", 0), "resolved_cases": by_status.get("APPROVED", 0) + by_status.get("REJECTED", 0),
                   "total_cases": sum(by_status.values())},
        "cases_over_time": [{"date": str(d), "count": c} for d, c in over_time],
        "risk_distribution": [{"label": lvl, "count": dist.get(lvl, 0)} for lvl in LEVELS],
        "fraud_by_transaction_type": [{"label": t, "count": c} for t, c in by_type],
        "fraud_by_location": [{"label": loc, "count": c} for loc, c in by_loc],
        "anomaly_trend": [{"date": str(d), "transactions": n, "flagged": int(f or 0)} for d, n, f in trend],
        "recent_high_risk_cases": [case_out(c) for c in recent],
    }


@router.get("/dashboard/analytics")
def analytics(db: Session = Depends(get_db), _: User = Depends(current_user)):
    total = db.query(func.count(Transaction.id)).scalar()
    flagged = db.query(func.count(Transaction.id)).filter(Transaction.risk_level.in_(("MEDIUM", "HIGH", "CRITICAL"))).scalar()
    scores = [s for (s,) in db.query(Transaction.risk_score).filter(Transaction.risk_score.isnot(None)).all()]
    hist = Counter(min(s // 10, 9) for s in scores)
    cases = db.query(FraudCase).all()
    txns = {t.id: t for t in db.query(Transaction).filter(Transaction.id.in_([c.transaction_id for c in cases])).all()} if cases else {}
    cat = Counter(txns[c.transaction_id].merchant_category for c in cases)
    hours = Counter(txns[c.transaction_id].occurred_at.hour for c in cases)
    new_dev = sum(any(i["code"] == "NEW_DEVICE" for i in c.risk_indicators) for c in cases)
    by_day = Counter(str(txns[c.transaction_id].occurred_at.date()) for c in cases)
    status = Counter(c.status for c in cases)
    return {
        "fraud_rate_percent": round(flagged / total * 100, 2) if total else 0.0, "total_transactions": total, "flagged_transactions": flagged,
        "risk_score_histogram": [{"bucket": f"{i * 10}-{i * 10 + 9 if i < 9 else 100}", "count": hist.get(i, 0)} for i in range(10)],
        "high_risk_trend": [{"date": d, "count": n} for d, n in sorted(by_day.items())],
        "fraud_by_merchant_category": [{"label": k, "count": v} for k, v in cat.most_common()],
        "fraud_by_device_novelty": [{"label": "New device", "count": new_dev}, {"label": "Known device", "count": len(cases) - new_dev}],
        "fraud_by_hour": [{"hour": h, "count": hours.get(h, 0)} for h in range(24)],
        "case_resolution_status": [{"label": s, "count": status.get(s, 0)} for s in STATUSES],
    }


AGENT_INFO = {"fraud_detection": ("Fraud Detection Agent", "Synthesizes the rule-based factors and ML anomaly score into an initial fraud verdict."),
              "transaction_analysis": ("Transaction Analysis Agent", "Compares amount, merchant, location, device and beneficiary against the customer's baseline."),
              "customer_risk": ("Customer Risk Agent", "Assesses the customer's profile and prior fraud cases."),
              "investigation": ("Investigation Agent", "Merges the earlier findings into one deduplicated summary."),
              "rag_policy": ("RAG Policy Agent", "Retrieves and cites the relevant banking policy sections."),
              "decision": ("Decision Recommendation Agent", "Recommends approve / escalate / block — advisory only; a human decides.")}


@router.get("/agents")
def agents(db: Session = Depends(get_db), _: User = Depends(current_user)):
    s = get_settings()
    rows = {r[0]: r for r in db.query(AgentExecution.agent_name, func.count(), func.avg(AgentExecution.confidence),
                                      func.avg(AgentExecution.execution_time_ms), func.sum(cast(AgentExecution.used_llm, Integer)))
            .group_by(AgentExecution.agent_name).all()}
    out = []
    for i, n in enumerate(AGENT_ORDER, 1):
        r = rows.get(n)
        runs, llm = (r[1], int(r[4] or 0)) if r else (0, 0)
        out.append({"name": n, "display_name": AGENT_INFO[n][0], "description": AGENT_INFO[n][1], "order": i, "total_runs": runs,
                    "avg_confidence": round(float(r[2]), 3) if r and r[2] is not None else None,
                    "avg_execution_time_ms": round(float(r[3]), 1) if r and r[3] is not None else None,
                    "llm_runs": llm, "deterministic_runs": runs - llm})
    return {"llm_provider": s.LLM_PROVIDER, "llm_configured": s.llm_available, "mode": "llm" if s.llm_available else "deterministic_fallback", "agents": out}


def _policies(db: Session) -> dict:
    cited = Counter()
    for (cites,) in db.query(Investigation.policy_citations).all():
        cited.update({c["slug"] for c in (cites or [])})
    docs: dict = {}
    for c in load_all():
        d = docs.setdefault(c.slug, {"id": c.slug, "title": c.document_title, "policy_id": c.policy_id, "category": c.category, "version": c.version,
                                     "sections": [], "full_sections": [], "relevant_cases": cited.get(c.slug, 0)})
        d["sections"].append(c.section)
        d["full_sections"].append({"section": c.section, "content": c.content})
    for d in docs.values():
        d["description"] = d["full_sections"][0]["content"][:240]
        d["chunk_count"] = len(d["sections"])
    return docs


@router.get("/policies")
def list_policies(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return [{k: v for k, v in d.items() if k != "full_sections"} for d in sorted(_policies(db).values(), key=lambda d: d["title"])]


@router.get("/policies/search")
def search_policies(q: str = Query(..., min_length=2, max_length=300), top_k: int = Query(5, ge=1, le=10), _: User = Depends(current_user)):
    available = policy_service.is_available()
    return {"query": q, "rag_available": available, "results": policy_service.retrieve(q, top_k) if available else []}


@router.get("/policies/{slug}")
def get_policy(slug: str, db: Session = Depends(get_db), _: User = Depends(current_user)):
    doc = _policies(db).get(slug)
    if not doc:
        raise HTTPException(404, f"Policy '{slug}' not found")
    return doc


# ---- system health -------------------------------------------------------------------------------------
CRITICAL = {"API", "PostgreSQL", "Vector DB (ChromaDB)", "Agent Orchestrator"}
RANK = {"ONLINE": 0, "DEGRADED": 1, "OFFLINE": 2}


def _svc(name, status, detail):
    return {"name": name, "status": status, "detail": detail}


@router.get("/system/health")
def system_health(db: Session = Depends(get_db), _: User = Depends(current_user)):
    s = get_settings()
    services = [_svc("API", "ONLINE", "Request reached this handler")]
    try:
        t0 = time.perf_counter()
        db.execute(text("SELECT 1"))
        services.append(_svc("PostgreSQL", "ONLINE", f"{db.bind.dialect.name} responded in {(time.perf_counter() - t0) * 1000:.1f}ms"))
    except Exception as exc:
        services.append(_svc("PostgreSQL", "OFFLINE", f"{type(exc).__name__}: connection failed"))
    if not s.REDIS_URL:
        services.append(_svc("Redis", "OFFLINE", "Not configured — nothing in this build depends on Redis"))
    else:
        try:
            import redis
            redis.from_url(s.REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5).ping()
            services.append(_svc("Redis", "ONLINE", "PING ok"))
        except Exception as exc:
            services.append(_svc("Redis", "OFFLINE", f"{type(exc).__name__} — optional, nothing in this build depends on it"))
    services.append(_svc(f"AI Service ({s.LLM_PROVIDER})", "ONLINE" if s.llm_available else "OFFLINE",
                         "API key configured; reachability is checked live on each agent call with automatic fallback" if s.llm_available
                         else "GROQ_API_KEY not configured — agents run on the deterministic fallback"))
    services.append(_svc("Vector DB (ChromaDB)", "ONLINE" if policy_service.is_available() else "OFFLINE",
                         "Policy collection and embedder loaded" if policy_service.is_available() else "Policy index not built (run python -m app.rag.policy_service)"))
    services.append(_svc("Agent Orchestrator", "ONLINE", f"LangGraph pipeline compiled ({len(GRAPH.get_graph().nodes)} nodes)"))
    overall = max((x for x in services if x["name"] in CRITICAL), key=lambda x: RANK[x["status"]])["status"]
    mem = psutil.virtual_memory()
    avg_ms, runs = db.query(func.avg(AgentExecution.execution_time_ms), func.count(AgentExecution.id)).first()
    m = metrics.snapshot()
    return {"overall_status": overall, "services": services, "metrics": {
        "cpu_percent": psutil.cpu_percent(interval=0.1), "memory_percent": mem.percent, "memory_used_mb": round(mem.used / 1048576, 1),
        "memory_total_mb": round(mem.total / 1048576, 1), "api_latency_ms_avg": m["latency_ms_avg"], "api_latency_ms_p95": m["latency_ms_p95"],
        "request_count": m["request_count"], "error_rate_percent": m["error_rate_percent"],
        "agent_avg_execution_time_ms": round(float(avg_ms), 1) if avg_ms is not None else None, "agent_execution_count": runs or 0,
        "uptime_seconds": m["uptime_seconds"]}}
