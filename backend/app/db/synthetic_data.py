"""Synthetic banking data (PKR, 8 Pakistani cities). No real personal data.

Customers get internally consistent baselines; transactions are mostly normal,
with a minority of suspicious (one deviation) and anomalous ones (new device +
new city + 10-30x amount + night hour + new beneficiary), some as velocity bursts.
Nothing is pre-labelled — the risk engine has to discover the anomalies.
"""

import random
from datetime import datetime, timedelta, timezone

CITIES = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar", "Quetta"]
CITY_WEIGHTS = [22, 26, 8, 9, 10, 9, 9, 7]
FIRST = [
    "Ahmed",
    "Ayesha",
    "Bilal",
    "Sana",
    "Usman",
    "Hira",
    "Hamza",
    "Zainab",
    "Ali",
    "Fatima",
    "Umar",
    "Mahnoor",
    "Hassan",
    "Areeba",
    "Zeeshan",
    "Sadia",
    "Faisal",
    "Komal",
    "Imran",
    "Rabia",
    "Kashif",
    "Amna",
    "Waqas",
    "Saba",
]
LAST = [
    "Khan",
    "Ahmed",
    "Raza",
    "Malik",
    "Siddiqui",
    "Sheikh",
    "Butt",
    "Chaudhry",
    "Qureshi",
    "Farooq",
    "Iqbal",
    "Hussain",
    "Abbasi",
    "Baig",
    "Awan",
    "Gill",
    "Mirza",
    "Javed",
    "Rashid",
    "Anwar",
]
CATEGORIES = {
    "Grocery": ("Al-Fatah Supermarket", "CARD_PAYMENT"),
    "Restaurant": ("Bundu Khan", "CARD_PAYMENT"),
    "Fuel": ("PSO Petrol Pump", "CARD_PAYMENT"),
    "Utility Bill": ("LESCO", "BILL_PAYMENT"),
    "Pharmacy": ("D.Watson Pharmacy", "CARD_PAYMENT"),
    "Clothing": ("Khaadi", "CARD_PAYMENT"),
    "ATM Withdrawal": ("Self-Service ATM", "WITHDRAWAL"),
    "Online Shopping": ("Daraz.pk", "ONLINE_PURCHASE"),
    "Electronics": ("Hafeez Center", "CARD_PAYMENT"),
    "Transfer": ("Raast Transfer", "TRANSFER"),
}
EVERYDAY = ["Grocery", "Restaurant", "Fuel", "Utility Bill", "Pharmacy", "Clothing", "ATM Withdrawal"]
OCCASIONAL = ["Online Shopping", "Electronics", "Transfer"]
DAY_HOUR_WEIGHTS = [1, 1, 1, 1, 1, 2, 4, 6, 7, 8, 8, 8, 8, 8, 8, 8, 8, 9, 9, 8, 6, 4, 3, 2]


def _device(rng):
    return "device-" + "".join(rng.choices("abcdef0123456789", k=10))


def _account(rng):
    return f"ACC-{rng.randint(10**9, 10**10 - 1)}"


def build_customers(rng: random.Random, count: int) -> list[dict]:
    out = []
    for i in range(1, count + 1):
        home = rng.choices(CITIES, CITY_WEIGHTS)[0]
        locs = [home] + ([rng.choice([c for c in CITIES if c != home])] if rng.random() < 0.15 else [])
        out.append(
            dict(
                customer_code=f"CUST-{i:06d}",
                full_name=f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                home_city=home,
                avg_transaction_amount=round(rng.uniform(5000, 20000), 2),
                typical_locations=locs,
                known_devices=[_device(rng) for _ in range(rng.choices([1, 2], [75, 25])[0])],
                known_beneficiaries=[_account(rng) for _ in range(rng.randint(0, 3))],
            )
        )
    return out


def _txn(rng, cust: dict, cid: int, kind: str, now: datetime, when: datetime | None = None) -> dict:
    cat = rng.choice(EVERYDAY) if rng.random() < 0.8 else rng.choice(OCCASIONAL)
    merchant, ttype = CATEGORIES[cat]
    avg = cust["avg_transaction_amount"]
    if kind == "normal":
        amount = max(200, rng.gauss(avg, avg * 0.35))
        loc = rng.choice(cust["typical_locations"])
        dev = rng.choice(cust["known_devices"])
        hour = rng.choices(range(24), DAY_HOUR_WEIGHTS)[0]
        ben = rng.choice(cust["known_beneficiaries"]) if ttype == "TRANSFER" and cust["known_beneficiaries"] else None
        days = 90
    elif kind == "suspicious":
        amount = avg * rng.uniform(3, 6)
        loc = rng.choice(cust["typical_locations"])
        dev = rng.choice(cust["known_devices"])
        hour = rng.choices(range(24), DAY_HOUR_WEIGHTS)[0]
        ben = _account(rng) if ttype == "TRANSFER" else None
        days = 90
    else:
        amount = avg * rng.uniform(10, 30)
        loc = rng.choice([c for c in CITIES if c not in cust["typical_locations"]])
        dev = _device(rng)
        hour = rng.choice([0, 1, 2, 3, 4])
        ben = _account(rng)
        days = 30
        ttype = "TRANSFER" if rng.random() < 0.6 else ttype
    if when is None:
        when = (now - timedelta(days=rng.randint(0, days))).replace(
            hour=hour, minute=rng.randint(0, 59), second=rng.randint(0, 59), microsecond=0
        )
    return dict(
        customer_id=cid,
        amount=round(max(100, amount), 2),
        currency="PKR",
        transaction_type=ttype,
        status="COMPLETED",
        merchant=merchant,
        merchant_category=cat,
        location=loc,
        device_id=dev,
        beneficiary_account=ben,
        occurred_at=when,
    )


def build_transactions(rng: random.Random, customers: list[dict], ids: list[int], target: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    counts = [max(3, round(rng.gauss(10, 4))) for _ in customers]
    scale = target / sum(counts)
    counts = [max(3, round(c * scale)) for c in counts]
    out, anomalous_customers = [], 0
    min_anomalous = min(40, max(1, len(customers) // 25))  # guarantee a findable population of anomalies
    for cust, cid, n in zip(customers, ids, counts):
        susp = rng.random() < 0.12
        anom = rng.random() < 0.06 or anomalous_customers < min_anomalous
        anomalous_customers += int(anom)
        for _ in range(max(1, n - int(susp) - int(anom))):
            out.append(_txn(rng, cust, cid, "normal", now))
        if susp:
            out.append(_txn(rng, cust, cid, "suspicious", now))
        if anom:
            a = _txn(rng, cust, cid, "anomalous", now)
            out.append(a)
            if rng.random() < 0.4:  # velocity burst on the same new device/city
                for k in range(rng.randint(2, 4)):
                    b = _txn(rng, cust, cid, "anomalous", now, when=a["occurred_at"] + timedelta(minutes=rng.randint(1, 8) * (k + 1)))
                    b["device_id"], b["location"] = a["device_id"], a["location"]
                    out.append(b)
    return out
