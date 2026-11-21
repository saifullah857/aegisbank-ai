from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import AUDIT, INVESTIGATE, current_user, log_audit, require_roles
from app.db.base import AgentExecution, AuditLog, FraudCase, Investigation, Transaction, User
from app.db.session import get_db
from app.services.agents import AGENT_ORDER, run_pipeline
from app.services.scoring import open_case_if_needed, score_and_store

router = APIRouter()
FALLBACK_NOTICE = "AI provider unavailable — running deterministic fallback analysis."


class AnalyzeRequest(BaseModel):
    transaction_id: int = Field(gt=0)


class DecisionBody(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


def find_case(db: Session, ref: str) -> FraudCase:
    """Accepts a numeric id ('12') or a case number ('FRD-2026-00012'). Called AFTER auth runs."""
    q = db.query(FraudCase)
    case = q.filter(FraudCase.id == int(ref)).first() if ref.isdigit() else q.filter(FraudCase.case_number == ref).first()
    if not case:
        raise HTTPException(404, f"Fraud case '{ref}' not found")
    return case


def case_out(c: FraudCase) -> dict:
    t, cu = c.transaction, c.customer
    return dict(id=c.id, case_number=c.case_number, status=c.status, risk_score=c.risk_score, risk_level=c.risk_level,
                risk_indicators=c.risk_indicators, created_at=c.created_at, has_investigation=c.investigation is not None,
                customer=dict(id=cu.id, code=cu.customer_code, name=cu.full_name, home_city=cu.home_city),
                transaction=dict(id=t.id, ref=t.transaction_ref, amount=float(t.amount), type=t.transaction_type, merchant=t.merchant,
                                 location=t.location, device_id=t.device_id, beneficiary_account=t.beneficiary_account,
                                 occurred_at=t.occurred_at))


def agent_out(a) -> dict:
    return dict(agent=a.agent, status=a.status, confidence=a.confidence, risk_findings=a.risk_findings, evidence=a.evidence,
                execution_time_ms=a.execution_time_ms, used_llm=a.used_llm)


def investigation_out(db: Session, c: FraudCase) -> dict:
    inv = c.investigation
    rows = {e.agent_name: e for e in db.query(AgentExecution).filter(AgentExecution.case_id == c.id)}
    agents = [dict(agent=n, status=rows[n].status, confidence=rows[n].confidence, risk_findings=rows[n].risk_findings,
                   evidence=rows[n].evidence, execution_time_ms=rows[n].execution_time_ms, used_llm=rows[n].used_llm)
              for n in AGENT_ORDER if n in rows]
    llm_used = any(a["used_llm"] for a in agents)
    return dict(case_number=c.case_number, case_status=c.status, summary=inv.summary, policy_citations=inv.policy_citations, ai_recommendation=inv.ai_recommendation,
                recommendation_reason=inv.recommendation_reason, confidence=inv.confidence, evidence=inv.evidence,
                decision_status=inv.decision_status, decided_by=inv.decided_by, decided_at=inv.decided_at,
                agents=agents, llm_used=llm_used, fallback_notice=None if llm_used else FALLBACK_NOTICE)


@router.get("/fraud/cases")
def list_cases(status: Literal["OPEN", "INVESTIGATING", "ESCALATED", "APPROVED", "REJECTED"] | None = None,
               risk_level: Literal["HIGH", "CRITICAL"] | None = None, page: int = Query(1, ge=1),
               page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(current_user)):
    q = db.query(FraudCase)
    if status:
        q = q.filter(FraudCase.status == status)
    if risk_level:
        q = q.filter(FraudCase.risk_level == risk_level)
    rows = q.order_by(FraudCase.risk_score.desc(), FraudCase.id).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": q.count(), "page": page, "page_size": page_size, "items": [case_out(c) for c in rows]}


@router.get("/fraud/cases/{case_ref}")
def get_case(case_ref: str, db: Session = Depends(get_db), _: User = Depends(current_user)):
    return case_out(find_case(db, case_ref))


@router.post("/fraud/analyze")
def analyze(body: AnalyzeRequest, db: Session = Depends(get_db), user: User = Depends(require_roles(*INVESTIGATE))):
    """Scores the transaction, opens a case if required, runs the six agents. Produces a RECOMMENDATION only."""
    txn = db.get(Transaction, body.transaction_id)
    if not txn:
        raise HTTPException(404, f"Transaction {body.transaction_id} not found")
    customer = txn.customer
    risk = score_and_store(db, txn, customer)
    case = open_case_if_needed(db, txn, risk)
    prior = db.query(FraudCase).filter(FraudCase.customer_id == customer.id, FraudCase.id != (case.id if case else -1)).count()
    outputs = run_pipeline(txn, customer, risk, prior)
    log_audit(db, user.username, "TRANSACTION_ANALYZED", case.id if case else None,
              details={"transaction_ref": txn.transaction_ref, "risk_level": risk.risk_level})

    if case is None:  # LOW/MEDIUM: show the reasoning but persist no case
        db.commit()
        return {"transaction_ref": txn.transaction_ref, "risk_score": risk.risk_score, "risk_level": risk.risk_level,
                "rule_score": risk.rule.risk_score, "ml_anomaly_score": risk.ml_score, "case_number": None, "investigation": None, "agents": [agent_out(outputs[n]) for n in AGENT_ORDER],
                "llm_used": any(o.used_llm for o in outputs.values()), "fallback_notice": None if any(o.used_llm for o in outputs.values()) else FALLBACK_NOTICE}

    inv = case.investigation
    if inv and inv.decision_status in ("APPROVED", "REJECTED"):  # final: return as-is, never overwrite a human decision
        db.commit()
        return {"transaction_ref": txn.transaction_ref, "risk_score": risk.risk_score, "risk_level": risk.risk_level,
                "case_number": case.case_number, "investigation": investigation_out(db, case)}

    db.query(AgentExecution).filter(AgentExecution.case_id == case.id).delete()
    for o in outputs.values():
        db.add(AgentExecution(case_id=case.id, agent_name=o.agent, status=o.status, confidence=o.confidence,
                              risk_findings=o.risk_findings, evidence=o.evidence, execution_time_ms=o.execution_time_ms, used_llm=o.used_llm))
    d, i = outputs["decision"], outputs["investigation"]
    fields = dict(summary=f"{risk.risk_level} risk case (score {risk.risk_score}/100). " + "; ".join(i.risk_findings[:4]),
                  ai_recommendation=d.risk_findings[0], recommendation_reason=d.risk_findings[1], confidence=d.confidence, evidence=i.evidence,
                  policy_citations=outputs["rag_policy"].citations)
    if inv:
        for k, v in fields.items():
            setattr(inv, k, v)
    else:
        db.add(Investigation(case_id=case.id, **fields))
    previous = case.status
    if case.status == "OPEN":
        case.status = "INVESTIGATING"
    log_audit(db, user.username, "INVESTIGATION_RUN", case.id, previous, case.status,
              {"recommendation": fields["ai_recommendation"], "confidence": fields["confidence"], "llm_used": any(o.used_llm for o in outputs.values())})
    db.commit()
    db.refresh(case)
    return {"transaction_ref": txn.transaction_ref, "risk_score": risk.risk_score, "risk_level": risk.risk_level,
            "rule_score": risk.rule.risk_score, "ml_anomaly_score": risk.ml_score,
            "case_number": case.case_number, "investigation": investigation_out(db, case)}


@router.get("/investigations/{case_ref}")
def get_investigation(case_ref: str, db: Session = Depends(get_db), _: User = Depends(current_user)):
    case = find_case(db, case_ref)
    if not case.investigation:
        raise HTTPException(404, f"No investigation has been run for case {case.case_number} yet")
    return investigation_out(db, case)


_DECISIONS = {"approve": ("APPROVED", "RECOMMENDATION_APPROVED"), "escalate": ("ESCALATED", "CASE_ESCALATED"),
              "reject": ("REJECTED", "RECOMMENDATION_REJECTED")}


@router.post("/investigations/{case_ref}/{decision}")
def decide(case_ref: str, decision: Literal["approve", "escalate", "reject"], body: DecisionBody | None = None,
           db: Session = Depends(get_db), user: User = Depends(require_roles(*INVESTIGATE))):
    """Human-in-the-loop: records the analyst's decision. It never freezes an account or moves money."""
    case = find_case(db, case_ref)
    inv = case.investigation
    if not inv:
        raise HTTPException(409, "Run the AI investigation before recording a decision.")
    if inv.decision_status in ("APPROVED", "REJECTED"):
        raise HTTPException(409, f"Case already {inv.decision_status.lower()}; the decision is final.")
    new_status, action = _DECISIONS[decision]
    if new_status == "ESCALATED" and inv.decision_status == "ESCALATED":
        raise HTTPException(409, "Case is already escalated.")
    previous = case.status
    inv.decision_status, inv.decided_by, inv.decided_at = new_status, user.username, datetime.now(timezone.utc)
    case.status = new_status
    log_audit(db, user.username, action, case.id, previous, new_status,
              {"notes": body.notes if body else None, "ai_recommendation": inv.ai_recommendation})
    db.commit()
    return {"case_number": case.case_number, "case_status": case.status, "decision_status": inv.decision_status,
            "decided_by": user.username, "decided_at": inv.decided_at}


@router.get("/audit")
def list_audit(case_id: int | None = Query(None, gt=0), actor: str | None = Query(None, max_length=64),
               action: str | None = Query(None, max_length=64), page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
               db: Session = Depends(get_db), _: User = Depends(require_roles(*AUDIT))):
    q = db.query(AuditLog)
    if case_id:
        q = q.filter(AuditLog.case_id == case_id)
    if actor:
        q = q.filter(AuditLog.actor == actor)
    if action:
        q = q.filter(AuditLog.action == action)
    rows = q.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": q.count(), "page": page, "page_size": page_size,
            "items": [dict(id=r.id, created_at=r.created_at, actor=r.actor, case_id=r.case_id, action=r.action,
                           previous_status=r.previous_status, new_status=r.new_status, details=r.details) for r in rows]}
