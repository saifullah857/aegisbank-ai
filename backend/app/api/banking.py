"""Accounts, ledger statements, held-transaction release/decline, and the ledger reconciliation check."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import AUDIT, INVESTIGATE, current_user, require_roles
from app.db.base import Account, LedgerEntry, Transaction, User
from app.db.session import get_db
from app.services import ledger, payments
from app.services.ledger import LedgerError

router = APIRouter()


class ReviewBody(BaseModel):
    notes: str | None = Field(default=None, max_length=500)


def account_out(a: Account) -> dict:
    return dict(id=a.id, account_number=a.account_number, customer_id=a.customer_id, account_type=a.account_type,
                currency=a.currency, balance=float(a.balance), status=a.status)


@router.get("/accounts")
def list_accounts(customer_id: int | None = Query(None, gt=0), db: Session = Depends(get_db), _: User = Depends(current_user)):
    q = select(Account).where(Account.account_type == "CUSTOMER").order_by(Account.id).limit(100)
    if customer_id:
        q = q.where(Account.customer_id == customer_id)
    return {"items": [account_out(a) for a in db.scalars(q)]}


@router.get("/accounts/{account_id}/ledger")
def account_ledger(account_id: int, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                   db: Session = Depends(get_db), _: User = Depends(current_user)):
    acct = db.get(Account, account_id)
    if not acct:
        raise HTTPException(404, f"Account {account_id} not found")
    q = db.query(LedgerEntry, Transaction.transaction_ref).join(Transaction, LedgerEntry.transaction_id == Transaction.id) \
        .filter(LedgerEntry.account_id == account_id)
    rows = q.order_by(LedgerEntry.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"account": account_out(acct), "total": q.count(), "page": page, "page_size": page_size,
            "items": [dict(id=e.id, transaction_ref=ref, direction=e.direction, amount=float(e.amount),
                           balance_after=float(e.balance_after), created_at=e.created_at) for e, ref in rows]}


def _review(db: Session, transaction_id: int, action, user: User, body: ReviewBody | None):
    try:
        txn = action(db, transaction_id, user.username, body.notes if body else None)
    except LedgerError as exc:
        db.rollback()
        raise HTTPException(exc.http_status, exc.message)
    db.commit()
    return {"transaction_ref": txn.transaction_ref, "status": txn.status, "failure_reason": txn.failure_reason}


@router.post("/transactions/{transaction_id}/release")
def release_transaction(transaction_id: int, body: ReviewBody | None = None, db: Session = Depends(get_db),
                        user: User = Depends(require_roles(*INVESTIGATE))):
    """Analyst lets a held (FLAGGED) transaction through. Funds are re-checked under lock before the ledger posts."""
    return _review(db, transaction_id, payments.release, user, body)


@router.post("/transactions/{transaction_id}/decline")
def decline_transaction(transaction_id: int, body: ReviewBody | None = None, db: Session = Depends(get_db),
                        user: User = Depends(require_roles(*INVESTIGATE))):
    """Analyst refuses a held transaction. Nothing ever moved, so nothing needs reversing."""
    return _review(db, transaction_id, payments.decline, user, body)


@router.get("/ledger/reconcile")
def reconcile(db: Session = Depends(get_db), _: User = Depends(require_roles(*AUDIT))):
    """Proves the books balance: total debits == total credits, and each balance == opening + credits - debits."""
    return ledger.reconcile(db)


