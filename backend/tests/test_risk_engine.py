from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

from app.services.risk_engine import evaluate

NOW = datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc)
CUST = NS(avg_transaction_amount=10000, known_devices=["dev-1"], typical_locations=["Lahore"], known_beneficiaries=["ACC-1"])


def txn(**kw):
    base = dict(amount=9000, device_id="dev-1", location="Lahore", beneficiary_account=None, merchant_category="Grocery",
                status="COMPLETED", occurred_at=NOW)
    base.update(kw)
    return NS(**base)


def codes(result):
    return {f.code for f in result.triggered}


def test_normal_is_low_with_no_factors():
    r = evaluate(txn(), CUST)
    assert (r.risk_score, r.risk_level, codes(r)) == (0, "LOW", set())


def test_medium_new_location_plus_new_beneficiary():
    r = evaluate(txn(location="Quetta", beneficiary_account="ACC-9"), CUST)
    assert codes(r) == {"NEW_LOCATION", "NEW_BENEFICIARY"} and (r.risk_score, r.risk_level) == (35, "MEDIUM")


def test_high_device_location_amount():
    r = evaluate(txn(device_id="new", location="Quetta", amount=80000), CUST)
    assert (r.risk_score, r.risk_level) == (60, "MEDIUM")  # 20+20+20 sits exactly on the MEDIUM boundary
    r = evaluate(txn(device_id="new", location="Quetta", amount=80000, beneficiary_account="ACC-9"), CUST)
    assert (r.risk_score, r.risk_level) == (75, "HIGH")


def test_critical_with_velocity():
    burst = [txn(occurred_at=NOW + timedelta(minutes=m)) for m in (2, 5)]
    r = evaluate(txn(device_id="new", location="Quetta", amount=80000, beneficiary_account="ACC-9"), CUST, burst)
    assert "HIGH_VELOCITY" in codes(r) and (r.risk_score, r.risk_level) == (90, "CRITICAL")


def test_score_is_clamped_to_100():
    hist = [txn(status="FAILED", occurred_at=NOW - timedelta(hours=h)) for h in (1, 2)]
    hist += [txn(occurred_at=NOW + timedelta(minutes=m)) for m in (1, 2)] + [txn(merchant_category="Fuel")] * 3
    r = evaluate(txn(device_id="n", location="Quetta", amount=99999, beneficiary_account="ACC-9", merchant_category="Electronics"), CUST, hist)
    assert codes(r) == {"NEW_DEVICE", "NEW_LOCATION", "UNUSUAL_AMOUNT", "HIGH_VELOCITY", "NEW_BENEFICIARY", "UNUSUAL_MERCHANT", "FAILED_ATTEMPTS"}
    assert r.risk_score == 100


def test_merchant_novelty_needs_enough_history():
    assert "UNUSUAL_MERCHANT" not in codes(evaluate(txn(merchant_category="Electronics"), CUST, [txn()] * 4))
    assert "UNUSUAL_MERCHANT" in codes(evaluate(txn(merchant_category="Electronics"), CUST, [txn()] * 6))


def test_failed_attempts_window_and_threshold():
    old = [txn(status="FAILED", occurred_at=NOW - timedelta(hours=30)) for _ in range(3)]
    assert "FAILED_ATTEMPTS" not in codes(evaluate(txn(), CUST, old))                       # outside 24h
    one = [txn(status="FAILED", occurred_at=NOW - timedelta(hours=1))]
    assert "FAILED_ATTEMPTS" not in codes(evaluate(txn(), CUST, one))                       # below threshold


def test_naive_and_aware_datetimes_do_not_crash():
    naive = txn(occurred_at=NOW.replace(tzinfo=None))
    evaluate(txn(), CUST, [naive])  # SQLite returns naive datetimes; must be handled


def test_every_factor_explains_itself():
    r = evaluate(txn(device_id="n"), CUST)
    assert all(f.detail for f in r.factors) and len(r.factors) == 7
