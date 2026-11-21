"""Create tables, demo users, and the synthetic dataset, then score every transaction.

    python -m app.db.seed [customers] [transactions]     (defaults: 1000 10000)
Idempotent: skips if customers already exist.
"""
import os
import random
import sys
from decimal import Decimal
from collections import defaultdict

from app.core.security import hash_password
from app.db.base import Account, Base, Customer, FraudCase, Transaction, User
from app.db.session import SessionLocal, engine
from app.db.synthetic_data import build_customers, build_transactions
from app.ml.features import extract_features
from app.ml.train import train_and_save
from app.services.ledger import CLEARING_NUMBER
from app.services.scoring import apply_assessment, assess, open_case_if_needed

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "AegisDemo123!")  # synthetic demo accounts only - override with the DEMO_PASSWORD env var on any public deployment
DEMO_USERS = [("admin", "System Administrator", "ADMIN"), ("analyst01", "Fraud Analyst One", "FRAUD_ANALYST"),
              ("auditor01", "Compliance Auditor", "AUDITOR"), ("viewer01", "Read Only Viewer", "VIEWER")]


def ensure_accounts(db) -> int:
    """Idempotent: the SYSTEM clearing account, plus one funded account for every customer that has none.
    The opening balance is large relative to the customer's average spend so realistic payments succeed."""
    created = 0
    if not db.query(Account).filter(Account.account_number == CLEARING_NUMBER).first():
        db.add(Account(account_number=CLEARING_NUMBER, customer_id=None, account_type="SYSTEM", opening_balance=0, balance=0))
        created += 1
    have = {cid for (cid,) in db.query(Account.customer_id).filter(Account.customer_id.isnot(None))}
    rng = random.Random(7)
    for c in db.query(Customer).order_by(Customer.id):
        if c.id in have:
            continue
        opening = (Decimal(str(float(c.avg_transaction_amount) or 5000.0)) * Decimal(rng.randint(25, 90))).quantize(Decimal("0.01"))
        db.add(Account(account_number=f"PK36AEGB{c.id:016d}", customer_id=c.id, account_type="CUSTOMER", opening_balance=opening, balance=opening))
        created += 1
    db.commit()
    return created


def seed(n_customers: int = 1000, n_txns: int = 10000, seed_value: int = 42, train_model: bool = True) -> dict:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        for u, name, role in DEMO_USERS:
            if not db.query(User).filter(User.username == u).first():
                db.add(User(username=u, full_name=name, role=role, hashed_password=hash_password(DEMO_PASSWORD)))
        db.commit()
        if db.query(Customer).count():
            return {"skipped": True, "accounts_created": ensure_accounts(db)}
        rng = random.Random(seed_value)
        cdicts = build_customers(rng, n_customers)
        customers = [Customer(**c) for c in cdicts]
        db.add_all(customers)
        db.commit()
        tdicts = build_transactions(rng, cdicts, [c.id for c in customers], n_txns)
        txns = [Transaction(transaction_ref=f"TMP-{i}", **t) for i, t in enumerate(tdicts)]
        db.add_all(txns)
        db.flush()
        by_cust = defaultdict(list)
        for t in txns:
            t.transaction_ref = f"TXN-{t.id:09d}"
            by_cust[t.customer_id].append(t)
        cmap = {c.id: c for c in customers}
        if train_model:  # train on the seeded behaviour, then score with rule+ML
            rows = [extract_features(t, cmap[cid], [o for o in g if o is not t]) for cid, g in by_cust.items() for t in g]
            train_and_save(rows)
        for cid, group in by_cust.items():
            for t in group:
                a = assess(t, cmap[cid], [o for o in group if o is not t])
                apply_assessment(t, a)
                open_case_if_needed(db, t, a)
        db.commit()
        return {"customers": len(customers), "transactions": len(txns), "cases": db.query(FraudCase).count(), "accounts_created": ensure_accounts(db)}
    finally:
        db.close()


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:3]] or [int(os.environ.get("SEED_CUSTOMERS", 1000)), int(os.environ.get("SEED_TXNS", 10000))]
    print(seed(*args))
