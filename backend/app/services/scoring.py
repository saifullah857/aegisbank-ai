"""Blend the deterministic rule score (60%, explainable) with the ML anomaly score (40%, catches subtler
combinations). With no trained model the rule score stands alone — the deterministic fallback."""
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.base import Customer, FraudCase, Transaction
from app.ml import inference
from app.ml.features import extract_features
from app.services.risk_engine import RiskFactor, RiskResult, classify, evaluate

RULE_WEIGHT, ML_WEIGHT = 0.6, 0.4


@dataclass
class Assessment:
    rule: RiskResult
    ml_score: float | None
    ml_is_anomaly: bool | None
    risk_score: int
    risk_level: str

    @property
    def factors(self) -> list[RiskFactor]:
        return self.rule.factors

    @property
    def triggered(self) -> list[RiskFactor]:
        return self.rule.triggered


def assess(txn, customer, history=(), detector=None) -> Assessment:
    history = list(history)
    rule = evaluate(txn, customer, history)
    detector = detector or inference.get_detector()
    if detector is None:
        return Assessment(rule, None, None, rule.risk_score, rule.risk_level)
    ml = detector.score_one(extract_features(txn, customer, history))
    combined = min(100, round(RULE_WEIGHT * rule.risk_score + ML_WEIGHT * ml["anomaly_score"] * 100))
    return Assessment(rule, ml["anomaly_score"], ml["is_anomaly"], combined, classify(combined))


def indicators(a: Assessment) -> list[dict]:
    return [{"code": f.code, "label": f.label, "points": f.points, "detail": f.detail} for f in a.triggered]


def apply_assessment(txn: Transaction, a: Assessment) -> None:
    txn.rule_risk_score, txn.ml_anomaly_score = a.rule.risk_score, a.ml_score
    txn.risk_score, txn.risk_level, txn.risk_indicators = a.risk_score, a.risk_level, indicators(a)
    if a.risk_level in ("HIGH", "CRITICAL"):
        txn.status = "FLAGGED"


def score_and_store(db: Session, txn: Transaction, customer: Customer) -> Assessment:
    history = db.query(Transaction).filter(Transaction.customer_id == customer.id, Transaction.id != txn.id).all()
    a = assess(txn, customer, history)
    apply_assessment(txn, a)
    return a


def open_case_if_needed(db: Session, txn: Transaction, a: Assessment) -> FraudCase | None:
    """HIGH/CRITICAL (combined) opens a case. Idempotent per transaction."""
    existing = db.query(FraudCase).filter(FraudCase.transaction_id == txn.id).first()
    if existing or a.risk_level not in ("HIGH", "CRITICAL"):
        return existing
    case = FraudCase(case_number=f"PENDING-{txn.id}", transaction_id=txn.id, customer_id=txn.customer_id,
                     risk_score=a.risk_score, risk_level=a.risk_level, status="OPEN", risk_indicators=indicators(a))
    db.add(case)
    db.flush()
    case.case_number = f"FRD-{datetime.now(timezone.utc).year}-{case.id:05d}"
    return case
