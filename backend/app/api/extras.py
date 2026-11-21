"""Customer detail + timelines, and the transaction-simulator / one-click-demo helpers.

The generators reuse the same synthetic-data builders as the seed, driven by the customer's REAL stored baseline,
so a "suspicious" transaction is suspicious relative to that customer — the risk engine still has to discover it.
"""
import random
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.cases import find_case
from app.core.deps import INVESTIGATE, current_user, log_audit, require_roles
from app.db.base import Account, Customer, FraudCase, Transaction, User
from app.db.session import get_db
from app.db.synthetic_data import CITIES, _txn
from app.services.scoring import open_case_if_needed, score_and_store

router = APIRouter()


def _txn_row(t: Transaction) -> dict:
    return dict(id=t.id, ref=t.transaction_ref, amount=float(t.amount), type=t.transaction_type, merchant=t.merchant,
                merchant_category=t.merchant_category, location=t.location, device_id=t.device_id,
                beneficiary_account=t.beneficiary_account, occurred_at=t.occurred_at, risk_score=t.risk_score,
                risk_level=t.risk_level, status=t.status, indicator_codes=[i["code"] for i in (t.risk_indicators or [])])


def _timeline(db: Session, customer: Customer, limit: int, until: datetime | None = None, highlight_id: int | None = None) -> list[dict]:
    q = db.query(Transaction).filter(Transaction.customer_id == customer.id)
    if until is not None:
        q = q.filter(Transaction.occurred_at <= until)
    rows = q.order_by(Transaction.occurred_at.desc(), Transaction.id.desc()).limit(limit).all()
    out = []
    for t in reversed(rows):
        r = _txn_row(t)
        r["known_device"] = t.device_id in customer.known_devices
        r["usual_location"] = t.location in customer.typical_locations
        r["is_anomaly"] = t.risk_level in ("HIGH", "CRITICAL") or t.id == highlight_id
        r["is_focus"] = t.id == highlight_id
        out.append(r)
    return out


@router.get("/customers/{customer_id}")
def customer_detail(customer_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    c = db.get(Customer, customer_id)
    if not c:
        raise HTTPException(404, f"Customer {customer_id} not found")
    total = db.query(func.count(Transaction.id)).filter(Transaction.customer_id == c.id).scalar()
    flagged = db.query(func.count(Transaction.id)).filter(Transaction.customer_id == c.id, Transaction.risk_level.in_(("HIGH", "CRITICAL"))).scalar()
    cases = db.query(FraudCase).filter(FraudCase.customer_id == c.id).order_by(FraudCase.id.desc()).all()
    return dict(id=c.id, customer_code=c.customer_code, full_name=c.full_name, home_city=c.home_city,
                avg_transaction_amount=float(c.avg_transaction_amount), typical_locations=c.typical_locations,
                known_devices=c.known_devices, known_beneficiaries_count=len(c.known_beneficiaries),
                total_transactions=total, flagged_transactions=flagged,
                accounts=[dict(id=a.id, account_number=a.account_number, balance=float(a.balance), currency=a.currency, status=a.status)
                          for a in db.query(Account).filter(Account.customer_id == c.id).order_by(Account.id)],
                cases=[dict(id=k.id, case_number=k.case_number, status=k.status, risk_level=k.risk_level, risk_score=k.risk_score) for k in cases],
                timeline=_timeline(db, c, 30))


@router.get("/fraud/cases/{case_ref}/timeline")
def case_timeline(case_ref: str, limit: int = Query(8, ge=3, le=30), db: Session = Depends(get_db), _: User = Depends(current_user)):
    """The customer's recent transactions up to and including the case transaction; the case transaction is flagged as the focus."""
    case = find_case(db, case_ref)
    return {"case_number": case.case_number, "customer_id": case.customer_id,
            "timeline": _timeline(db, case.customer, limit, until=case.transaction.occurred_at, highlight_id=case.transaction_id)}


class SimulateRequest(BaseModel):
    customer_id: int = Field(gt=0)
    kind: Literal["normal", "suspicious", "anomalous"] = "normal"


def _generate(customer: Customer, kind: str) -> dict:
    rng = random.Random()
    base = dict(avg_transaction_amount=float(customer.avg_transaction_amount), typical_locations=list(customer.typical_locations) or [customer.home_city],
                known_devices=list(customer.known_devices) or ["device-unknown"], known_beneficiaries=list(customer.known_beneficiaries))
    now = datetime.now(timezone.utc)
    when = now
    if kind == "anomalous":  # a night-time hit today (never in the future)
        when = now.replace(hour=rng.choice([1, 2, 3]), minute=rng.randint(0, 59), second=0, microsecond=0)
        if when > now:
            when -= timedelta(days=1)
    t = _txn(rng, base, customer.id, kind, now, when=when)
    if kind == "anomalous":
        t["location"] = rng.choice([c for c in CITIES if c not in base["typical_locations"]] or CITIES)
        if t["transaction_type"] != "TRANSFER":
            t["transaction_type"] = "TRANSFER"
            t["merchant"], t["merchant_category"] = "Raast Transfer", "Transfer"
    t.pop("customer_id"), t.pop("currency"), t.pop("status")
    t["occurred_at"] = t["occurred_at"].isoformat()
    t["customer_id"] = customer.id
    return t


@router.post("/simulator/generate")
def simulator_generate(body: SimulateRequest, db: Session = Depends(get_db), _: User = Depends(require_roles(*INVESTIGATE))):
    """Builds a draft transaction from the customer's baseline. Nothing is stored until the analyst submits it."""
    c = db.get(Customer, body.customer_id)
    if not c:
        raise HTTPException(404, f"Customer {body.customer_id} not found")
    return _generate(c, body.kind)


@router.post("/demo/transaction", status_code=201)
def demo_transaction(db: Session = Depends(get_db), user: User = Depends(require_roles(*INVESTIGATE))):
    """One-click demo, step 1: create a fresh synthetic anomalous transaction for a random customer, score it
    (rule + ML) and open its case. The UI then calls /fraud/analyze to run the agents. Fully repeatable."""
    count = db.query(func.count(Customer.id)).scalar()
    if not count:
        raise HTTPException(409, "No customers exist; run the seed first (python -m app.db.seed).")
    customer = db.query(Customer).offset(random.randrange(count)).first()
    d = _generate(customer, "anomalous")
    d["occurred_at"] = datetime.fromisoformat(d["occurred_at"])
    txn = Transaction(transaction_ref=f"PENDING-{datetime.now(timezone.utc).timestamp()}", currency="PKR", status="COMPLETED", **d)
    db.add(txn)
    db.flush()
    txn.transaction_ref = f"TXN-{txn.id:09d}"
    result = score_and_store(db, txn, customer)
    case = open_case_if_needed(db, txn, result)
    log_audit(db, user.username, "DEMO_TRANSACTION_CREATED", case.id if case else None, details={"transaction_ref": txn.transaction_ref, "synthetic": True})
    db.commit()
    return {"transaction_id": txn.id, "transaction_ref": txn.transaction_ref, "customer_id": customer.id, "customer_name": customer.full_name,
            "amount": float(txn.amount), "location": txn.location, "risk_score": txn.risk_score, "rule_score": txn.rule_risk_score,
            "ml_anomaly_score": txn.ml_anomaly_score, "risk_level": txn.risk_level, "risk_indicators": txn.risk_indicators,
            "case_number": case.case_number if case else None}
