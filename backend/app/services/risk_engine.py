"""Deterministic, rule-based fraud scoring.

Every factor is computed from the transaction, the customer's stored behavioral
baseline, and the customer's other transactions — nothing is hardcoded per
transaction. Also serves as the deterministic fallback when no LLM is available.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

WEIGHTS = {
    "NEW_DEVICE": 20, "NEW_LOCATION": 20, "UNUSUAL_AMOUNT": 20, "HIGH_VELOCITY": 15,
    "NEW_BENEFICIARY": 15, "UNUSUAL_MERCHANT": 10, "FAILED_ATTEMPTS": 10,
}
UNUSUAL_AMOUNT_MULTIPLIER = 5.0
VELOCITY_WINDOW = timedelta(minutes=15)
VELOCITY_MIN_COUNT = 3
MERCHANT_MIN_HISTORY = 5
MERCHANT_MAX_SHARE = 0.10
FAILED_WINDOW = timedelta(hours=24)
FAILED_MIN_COUNT = 2


@dataclass
class RiskFactor:
    code: str
    label: str
    points: int
    triggered: bool
    detail: str


@dataclass
class RiskResult:
    risk_score: int
    risk_level: str
    factors: list[RiskFactor] = field(default_factory=list)

    @property
    def triggered(self) -> list[RiskFactor]:
        return [f for f in self.factors if f.triggered]


def classify(score: int) -> str:
    if score <= 30:
        return "LOW"
    if score <= 60:
        return "MEDIUM"
    if score <= 80:
        return "HIGH"
    return "CRITICAL"


def _aware(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC so comparisons never mix kinds."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def evaluate(txn, customer, history=()) -> RiskResult:
    """txn/customer/history are ORM rows or any objects with the same attributes.
    `history` = the customer's OTHER transactions."""
    history = list(history)
    when = _aware(txn.occurred_at)
    factors: list[RiskFactor] = []

    def add(code, label, triggered, detail):
        factors.append(RiskFactor(code, label, WEIGHTS[code], triggered, detail))

    new_dev = txn.device_id not in customer.known_devices
    add("NEW_DEVICE", "New Device", new_dev,
        f"Device '{txn.device_id}' is not one of the customer's {len(customer.known_devices)} known device(s)."
        if new_dev else "Device recognized from customer history.")

    new_loc = txn.location not in customer.typical_locations
    add("NEW_LOCATION", "Unusual Location", new_loc,
        f"'{txn.location}' is outside the customer's typical locations {list(customer.typical_locations)}."
        if new_loc else "Location matches the customer's typical activity.")

    avg = float(customer.avg_transaction_amount) or 1.0
    ratio = float(txn.amount) / avg
    big = ratio > UNUSUAL_AMOUNT_MULTIPLIER
    add("UNUSUAL_AMOUNT", "Unusual Amount", big,
        f"{float(txn.amount):,.0f} PKR is {ratio:.1f}x the customer's average of {avg:,.0f} PKR "
        f"(threshold {UNUSUAL_AMOUNT_MULTIPLIER:g}x)." if big else f"Amount is {ratio:.1f}x the average — within range.")

    nearby = sum(1 for t in history if abs(_aware(t.occurred_at) - when) <= VELOCITY_WINDOW) + 1
    fast = nearby >= VELOCITY_MIN_COUNT
    add("HIGH_VELOCITY", "High Transaction Velocity", fast,
        f"{nearby} transactions within ±15 minutes (threshold {VELOCITY_MIN_COUNT})." if fast
        else f"Only {nearby} transaction(s) in the surrounding 15 minutes.")

    new_ben = bool(txn.beneficiary_account) and txn.beneficiary_account not in customer.known_beneficiaries
    add("NEW_BENEFICIARY", "New Beneficiary", new_ben,
        f"Beneficiary '{txn.beneficiary_account}' has not been used by this customer before."
        if new_ben else "No new beneficiary involved.")

    if len(history) < MERCHANT_MIN_HISTORY:
        add("UNUSUAL_MERCHANT", "Unusual Merchant Category", False, "Not enough history to judge category novelty.")
    else:
        share = sum(1 for t in history if t.merchant_category == txn.merchant_category) / len(history)
        rare = share < MERCHANT_MAX_SHARE
        add("UNUSUAL_MERCHANT", "Unusual Merchant Category", rare,
            f"'{txn.merchant_category}' is only {share:.0%} of this customer's {len(history)} past transactions."
            if rare else f"'{txn.merchant_category}' is a regular category for this customer ({share:.0%}).")

    failed = sum(1 for t in history if t.status == "FAILED" and timedelta(0) <= when - _aware(t.occurred_at) <= FAILED_WINDOW)
    many = failed >= FAILED_MIN_COUNT
    add("FAILED_ATTEMPTS", "Recent Failed Attempts", many,
        f"{failed} failed attempt(s) in the preceding 24h (threshold {FAILED_MIN_COUNT})." if many
        else f"{failed} failed attempt(s) in the preceding 24h.")

    score = min(100, sum(f.points for f in factors if f.triggered))
    return RiskResult(score, classify(score), factors)
