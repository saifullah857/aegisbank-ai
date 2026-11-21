"""Numeric features for the Isolation Forest, derived from the transaction, the customer baseline and history."""
from datetime import timedelta, timezone

FEATURE_NAMES = ["amount", "amount_deviation", "velocity_15min", "hour_of_day", "location_deviation", "device_novelty", "txn_frequency_daily"]


def _aware(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def extract_features(txn, customer, history=()) -> list[float]:
    history = list(history)
    when = _aware(txn.occurred_at)
    avg = float(customer.avg_transaction_amount) or 1.0
    amount = float(txn.amount)
    velocity = sum(1 for t in history if abs(_aware(t.occurred_at) - when) <= timedelta(minutes=15)) + 1
    if history:
        times = [_aware(t.occurred_at) for t in history] + [when]
        span_days = max(1.0, (max(times) - min(times)).total_seconds() / 86400)
        frequency = (len(history) + 1) / span_days
    else:
        frequency = 1.0
    return [amount, (amount - avg) / avg, float(velocity), float(when.hour),
            0.0 if txn.location in customer.typical_locations else 1.0,
            0.0 if txn.device_id in customer.known_devices else 1.0, frequency]
