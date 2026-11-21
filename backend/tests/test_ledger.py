"""Double-entry ledger, held funds, idempotency and failure handling."""
from decimal import Decimal

from app.db.base import Account, AuditLog, Customer, LedgerEntry, Transaction
from app.services import ledger

API = "/api/v1"
NORMAL = dict(amount=7500, transaction_type="CARD_PAYMENT", merchant="Al-Fatah", merchant_category="Grocery", location="Lahore", device_id="device-known")
ANOMALOUS = dict(amount=400000, transaction_type="TRANSFER", merchant="Raast Transfer", merchant_category="Transfer", location="Quetta",
                 device_id="device-evil", beneficiary_account="ACC-9999999999", occurred_at="2026-01-05T02:30:00+00:00")


def acct(db, customer):
    return db.query(Account).filter(Account.customer_id == customer.id).one()


def post(client, headers, customer, extra=None, key=None, **over):
    h = {**headers, **({"Idempotency-Key": key} if key else {})}
    return client.post(f"{API}/transactions", json={"customer_id": customer.id, **NORMAL, **over, **(extra or {})}, headers=h)


def test_normal_payment_moves_money_with_balanced_entries(client, analyst, db, world):
    start = Decimal(str(acct(db, world).balance))
    r = post(client, analyst, world)
    assert r.status_code == 201 and r.json()["status"] == "COMPLETED"
    db.expire_all()
    assert Decimal(str(acct(db, world).balance)) == start - Decimal("7500.00")
    entries = db.query(LedgerEntry).filter(LedgerEntry.transaction_id == r.json()["id"]).all()
    assert sorted(e.direction for e in entries) == ["CREDIT", "DEBIT"]
    assert len({e.amount for e in entries}) == 1


def test_deposit_credits_the_customer(client, analyst, db, world):
    start = Decimal(str(acct(db, world).balance))
    assert post(client, analyst, world, transaction_type="DEPOSIT", amount=1000).status_code == 201
    db.expire_all()
    assert Decimal(str(acct(db, world).balance)) == start + Decimal("1000.00")


def test_insufficient_funds_fails_records_attempt_and_moves_nothing(client, analyst, db, world):
    a = acct(db, world)
    a.balance = 100
    db.commit()
    r = post(client, analyst, world, amount=5000)
    assert r.status_code == 422 and r.json()["code"] == "insufficient_funds"
    db.expire_all()
    assert Decimal(str(acct(db, world).balance)) == Decimal("100.00")
    failed = db.query(Transaction).filter(Transaction.status == "FAILED").one()
    assert "Insufficient" in failed.failure_reason
    assert db.query(LedgerEntry).count() == 0


def test_idempotency_key_prevents_double_spend(client, analyst, db, world):
    start = Decimal(str(acct(db, world).balance))
    first = post(client, analyst, world, key="retry-abc-123")
    second = post(client, analyst, world, key="retry-abc-123")
    assert first.status_code == 201 and second.status_code == 200
    assert second.json()["id"] == first.json()["id"] and second.json()["replayed"] is True
    db.expire_all()
    assert Decimal(str(acct(db, world).balance)) == start - Decimal("7500.00")  # charged once


def test_idempotency_key_reused_for_different_request_is_rejected(client, analyst, world):
    assert post(client, analyst, world, key="same-key-1").status_code == 201
    assert post(client, analyst, world, key="same-key-1", amount=9999).status_code == 409


def test_high_risk_payment_is_held_then_released(client, analyst, db, world):
    start = Decimal(str(acct(db, world).balance))
    r = post(client, analyst, world, extra=ANOMALOUS).json()
    assert r["status"] == "FLAGGED" and r["case_number"]
    db.expire_all()
    assert Decimal(str(acct(db, world).balance)) == start  # nothing moved while held
    rel = client.post(f"{API}/transactions/{r['id']}/release", json={"notes": "customer confirmed by phone"}, headers=analyst)
    assert rel.status_code == 200 and rel.json()["status"] == "COMPLETED"
    db.expire_all()
    assert Decimal(str(acct(db, world).balance)) == start - Decimal("400000.00")
    assert db.query(AuditLog).filter(AuditLog.action == "TRANSACTION_RELEASED").count() == 1
    assert client.post(f"{API}/transactions/{r['id']}/release", headers=analyst).status_code == 409  # cannot release twice


def test_held_payment_can_be_declined_without_moving_money(client, analyst, db, world):
    start = Decimal(str(acct(db, world).balance))
    r = post(client, analyst, world, extra=ANOMALOUS).json()
    d = client.post(f"{API}/transactions/{r['id']}/decline", json={"notes": "fraud"}, headers=analyst)
    assert d.status_code == 200 and d.json()["status"] == "DECLINED"
    db.expire_all()
    assert Decimal(str(acct(db, world).balance)) == start


def test_release_rechecks_funds(client, analyst, db, world):
    r = post(client, analyst, world, extra=ANOMALOUS).json()
    a = acct(db, world)
    a.balance = 10  # money left the account while the payment sat on hold
    db.commit()
    assert client.post(f"{API}/transactions/{r['id']}/release", headers=analyst).status_code == 422
    db.expire_all()
    assert db.get(Transaction, r["id"]).status == "FLAGGED"


def test_internal_transfer_credits_the_other_customer(client, analyst, db, world):
    other = Customer(customer_code="CUST-T2", full_name="Other", home_city="Lahore", avg_transaction_amount=8000,
                     typical_locations=["Lahore"], known_devices=["device-known"], known_beneficiaries=["PK36AEGBTEST000000000002"])
    db.add(other)
    db.commit()
    db.add(Account(account_number="PK36AEGBTEST000000000002", customer_id=other.id, opening_balance=1000, balance=1000))
    db.commit()
    r = post(client, analyst, world, transaction_type="TRANSFER", amount=2000, beneficiary_account="PK36AEGBTEST000000000002",
             merchant="Raast Transfer", merchant_category="Transfer")
    assert r.status_code == 201 and r.json()["status"] == "COMPLETED", r.text
    db.expire_all()
    assert Decimal(str(acct(db, other).balance)) == Decimal("3000.00")


def test_transfer_to_own_account_is_rejected(client, analyst, db, world):
    r = post(client, analyst, world, transaction_type="TRANSFER", beneficiary_account="PK36AEGBTEST000000000001")
    assert r.status_code == 422 and r.json()["code"] == "same_account"


def test_reconcile_balances_after_activity_and_detects_tampering(client, analyst, auditor, db, world):
    post(client, analyst, world)
    post(client, analyst, world, transaction_type="DEPOSIT", amount=500)
    ok = client.get(f"{API}/ledger/reconcile", headers=auditor).json()
    assert ok["balanced"] is True and ok["mismatches"] == []
    a = acct(db, world)
    a.balance = Decimal("1.00")  # someone edits a balance behind the ledger's back
    db.commit()
    bad = client.get(f"{API}/ledger/reconcile", headers=auditor).json()
    assert bad["balanced"] is False and bad["mismatches"][0]["account_number"] == a.account_number


def test_reconcile_is_restricted_and_viewers_cannot_release(client, analyst, viewer, world):
    assert client.get(f"{API}/ledger/reconcile", headers=viewer).status_code == 403
    r = post(client, analyst, world, extra=ANOMALOUS).json()
    assert client.post(f"{API}/transactions/{r['id']}/release", headers=viewer).status_code == 403


def test_customer_without_account_gets_clear_error(client, analyst, db, world):
    db.query(Account).filter(Account.customer_id == world.id).delete()
    db.commit()
    assert post(client, analyst, world).status_code == 409


def test_money_helper_rounds_half_up():
    assert ledger.money(0.125) == Decimal("0.13") and ledger.money("10") == Decimal("10.00")


def test_ledger_statement_endpoint(client, analyst, viewer, db, world):
    post(client, analyst, world)
    a = acct(db, world)
    body = client.get(f"{API}/accounts/{a.id}/ledger", headers=viewer).json()
    assert body["total"] == 1 and body["items"][0]["direction"] == "DEBIT"
