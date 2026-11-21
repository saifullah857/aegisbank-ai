"""Double-entry ledger.

Rules this module enforces:
  * Money is Decimal, rounded to 2 places (never float).
  * Every posted transaction writes exactly one DEBIT and one CREDIT of the same amount, so the books always balance.
    Money entering/leaving the bank (cash, merchants, other banks) is booked against the SYSTEM "CLEARING" account.
  * Account rows are locked (SELECT ... FOR UPDATE on PostgreSQL) in ascending-id order before the balance is read, so two
    concurrent payments cannot both spend the same money, and two opposite transfers cannot deadlock.
  * A customer account can never go below zero; the CLEARING account may.
  * Posting happens inside the caller's DB transaction: either the whole thing commits or none of it does.
"""
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Account, LedgerEntry, Transaction

CENT = Decimal("0.01")
CLEARING_NUMBER = "PK00AEGSCLEARING000000"
CREDIT_TYPES = {"DEPOSIT"}  # everything else takes money out of the customer's account


class LedgerError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 409):
        super().__init__(message)
        self.code, self.message, self.http_status = code, message, http_status


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def is_debit(transaction_type: str) -> bool:
    return transaction_type not in CREDIT_TYPES


def clearing_account(db: Session) -> Account:
    acct = db.scalar(select(Account).where(Account.account_number == CLEARING_NUMBER))
    if acct is None:
        raise LedgerError("ledger_not_initialised", "The ledger has not been initialised (run the seed / ensure_accounts).", 503)
    return acct


def customer_account(db: Session, customer_id: int) -> Account | None:
    return db.scalar(select(Account).where(Account.customer_id == customer_id, Account.account_type == "CUSTOMER",
                                           Account.status != "CLOSED").order_by(Account.id).limit(1))


def lock_accounts(db: Session, ids: list[int]) -> dict[int, Account]:
    """Lock + load accounts in ascending id order (deadlock-free). SQLite ignores FOR UPDATE; PostgreSQL honours it."""
    rows = db.scalars(select(Account).where(Account.id.in_(sorted(set(ids)))).order_by(Account.id).with_for_update()).all()
    return {a.id: a for a in rows}


def resolve_destination(db: Session, txn: Transaction, source: Account) -> Account | None:
    """A TRANSFER whose beneficiary is one of OUR account numbers credits that account; anything else goes to clearing."""
    if txn.transaction_type != "TRANSFER" or not txn.beneficiary_account:
        return None
    dest = db.scalar(select(Account).where(Account.account_number == txn.beneficiary_account, Account.account_type == "CUSTOMER"))
    if dest is not None and dest.id == source.id:
        raise LedgerError("same_account", "Source and beneficiary account are the same.", 422)
    return dest


def available_check(source: Account, amount: Decimal, transaction_type: str) -> None:
    if source.status != "ACTIVE":
        raise LedgerError("account_not_active", f"Account {source.account_number} is {source.status.lower()}.", 409)
    if is_debit(transaction_type) and money(source.balance) < amount:
        raise LedgerError("insufficient_funds",
                          f"Insufficient funds: balance {money(source.balance):,.2f} PKR, requested {amount:,.2f} PKR.", 422)


def post(db: Session, txn: Transaction, source: Account, destination: Account | None, clearing: Account) -> list[LedgerEntry]:
    """Move the money. Caller must already hold the locks and have run available_check()."""
    amount = money(txn.amount)
    if destination is not None and destination.status != "ACTIVE":
        raise LedgerError("beneficiary_not_active", f"Beneficiary account {destination.account_number} is {destination.status.lower()}.", 409)
    debit_acct, credit_acct = (clearing, source) if not is_debit(txn.transaction_type) else (source, destination or clearing)
    entries = []
    for acct, direction in ((debit_acct, "DEBIT"), (credit_acct, "CREDIT")):
        acct.balance = money(acct.balance) + (amount if direction == "CREDIT" else -amount)
        entries.append(LedgerEntry(transaction_id=txn.id, account_id=acct.id, direction=direction, amount=amount, balance_after=acct.balance))
    db.add_all(entries)
    return entries


def reconcile(db: Session) -> dict:
    """Audit check: (1) debits == credits overall, (2) every account's balance == opening + credits - debits."""
    sums = {(a, d): money(v) for a, d, v in db.execute(
        select(LedgerEntry.account_id, LedgerEntry.direction, func.sum(LedgerEntry.amount)).group_by(LedgerEntry.account_id, LedgerEntry.direction))}
    total_debits = sum((v for (_, d), v in sums.items() if d == "DEBIT"), Decimal("0"))
    total_credits = sum((v for (_, d), v in sums.items() if d == "CREDIT"), Decimal("0"))
    mismatches, accounts = [], db.scalars(select(Account)).all()
    for a in accounts:
        expected = money(a.opening_balance) + sums.get((a.id, "CREDIT"), Decimal("0")) - sums.get((a.id, "DEBIT"), Decimal("0"))
        if expected != money(a.balance):
            mismatches.append({"account_number": a.account_number, "expected": float(expected), "actual": float(money(a.balance))})
    return {"balanced": total_debits == total_credits and not mismatches, "total_debits": float(total_debits),
            "total_credits": float(total_credits), "accounts_checked": len(accounts), "mismatches": mismatches}
