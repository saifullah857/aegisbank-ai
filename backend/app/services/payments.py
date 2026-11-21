"""Transaction lifecycle: score -> (hold | fail | post to ledger) -> audit, all in ONE database transaction.

Statuses
  COMPLETED  money moved (ledger entries exist)
  FLAGGED    HIGH/CRITICAL risk: funds NOT moved; waiting for an analyst to release or decline
  FAILED     rejected before any money moved (insufficient funds, frozen account, ...) - still recorded, feeds the risk engine
  DECLINED   an analyst refused a held transaction; no money moved
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import log_audit
from app.db.base import Account, Customer, FraudCase, Transaction
from app.services import ledger
from app.services.ledger import LedgerError, money
from app.services.scoring import open_case_if_needed, score_and_store


@dataclass
class Outcome:
    txn: Transaction
    case: FraudCase | None
    replayed: bool = False
    error: LedgerError | None = None


def _replay(db: Session, existing: Transaction, customer_id: int, fields: dict) -> Outcome:
    same = (existing.customer_id == customer_id and money(existing.amount) == money(fields["amount"])
            and existing.transaction_type == fields["transaction_type"] and existing.beneficiary_account == fields.get("beneficiary_account"))
    if not same:
        raise LedgerError("idempotency_key_reuse", "This Idempotency-Key was already used for a different request.", 409)
    return Outcome(existing, db.scalar(select(FraudCase).where(FraudCase.transaction_id == existing.id)), replayed=True)


def submit(db: Session, customer: Customer, fields: dict, idempotency_key: str | None, actor: str) -> Outcome:
    """fields = validated TransactionCreate data (amount, type, merchant, ..., occurred_at). Caller commits."""
    if idempotency_key:
        existing = db.scalar(select(Transaction).where(Transaction.idempotency_key == idempotency_key))
        if existing:
            return _replay(db, existing, customer.id, fields)

    source = ledger.customer_account(db, customer.id)
    if source is None:
        raise LedgerError("no_account", f"Customer {customer.id} has no active account.", 409)
    clearing = ledger.clearing_account(db)

    when = fields.pop("occurred_at", None) or datetime.now(timezone.utc)
    txn = Transaction(transaction_ref=f"PENDING-{datetime.now(timezone.utc).timestamp()}", currency="PKR", status="COMPLETED",
                      occurred_at=when, account_id=source.id, idempotency_key=idempotency_key, **fields)
    db.add(txn)
    try:
        db.flush()
    except IntegrityError:  # two identical requests raced; the unique index picked one winner
        db.rollback()
        existing = db.scalar(select(Transaction).where(Transaction.idempotency_key == idempotency_key)) if idempotency_key else None
        if existing is None:
            raise
        return _replay(db, existing, customer.id, fields)
    txn.transaction_ref = f"TXN-{txn.id:09d}"

    assessment = score_and_store(db, txn, customer)  # sets risk fields; status -> FLAGGED for HIGH/CRITICAL
    case = open_case_if_needed(db, txn, assessment)
    amount = money(txn.amount)
    error = None
    try:
        dest = ledger.resolve_destination(db, txn, source)
        locked = ledger.lock_accounts(db, [source.id, clearing.id] + ([dest.id] if dest else []))
        src, clr, dst = locked[source.id], locked[clearing.id], locked.get(dest.id) if dest else None
        ledger.available_check(src, amount, txn.transaction_type)
        if txn.status == "FLAGGED":
            log_audit(db, actor, "TRANSACTION_HELD", case.id if case else None,
                      details={"transaction_ref": txn.transaction_ref, "risk_level": txn.risk_level, "amount": float(amount)})
        else:
            ledger.post(db, txn, src, dst, clr)
            log_audit(db, actor, "TRANSACTION_POSTED", None, details={"transaction_ref": txn.transaction_ref, "amount": float(amount)})
    except LedgerError as exc:
        txn.status, txn.failure_reason, error = "FAILED", exc.message[:255], exc
        log_audit(db, actor, "TRANSACTION_FAILED", case.id if case else None,
                  details={"transaction_ref": txn.transaction_ref, "reason": exc.code})
    db.flush()
    return Outcome(txn, case, error=error)


def _held(db: Session, transaction_id: int) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if txn is None:
        raise LedgerError("not_found", f"Transaction {transaction_id} not found", 404)
    if txn.status != "FLAGGED" or txn.account_id is None:
        raise LedgerError("not_on_hold", f"Transaction {txn.transaction_ref} is {txn.status} - only a ledger-backed FLAGGED (held) transaction can be released or declined.", 409)
    return txn


def _case_id(db: Session, txn: Transaction) -> int | None:
    return db.scalar(select(FraudCase.id).where(FraudCase.transaction_id == txn.id))


def release(db: Session, transaction_id: int, actor: str, notes: str | None) -> Transaction:
    """Analyst approves a held transaction: re-check funds under lock, then move the money."""
    txn = _held(db, transaction_id)
    clearing = ledger.clearing_account(db)
    source_id = txn.account_id
    probe = db.get(Account, source_id)
    dest = ledger.resolve_destination(db, txn, probe)
    locked = ledger.lock_accounts(db, [source_id, clearing.id] + ([dest.id] if dest else []))
    src = locked[source_id]
    ledger.available_check(src, money(txn.amount), txn.transaction_type)
    ledger.post(db, txn, src, locked.get(dest.id) if dest else None, locked[clearing.id])
    txn.status = "COMPLETED"
    log_audit(db, actor, "TRANSACTION_RELEASED", _case_id(db, txn), "FLAGGED", "COMPLETED", {"transaction_ref": txn.transaction_ref, "notes": notes})
    db.flush()
    return txn


def decline(db: Session, transaction_id: int, actor: str, notes: str | None) -> Transaction:
    txn = _held(db, transaction_id)
    txn.status, txn.failure_reason = "DECLINED", (f"Declined by analyst: {notes}" if notes else "Declined by analyst")[:255]
    log_audit(db, actor, "TRANSACTION_DECLINED", _case_id(db, txn), "FLAGGED", "DECLINED", {"transaction_ref": txn.transaction_ref, "notes": notes})
    db.flush()
    return txn
