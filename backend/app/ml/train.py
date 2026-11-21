"""Train the Isolation Forest on the stored transactions.   python -m app.ml.train"""
from collections import defaultdict

from app.db.base import Customer, Transaction
from app.db.session import SessionLocal
from app.ml import inference
from app.ml.features import extract_features
from app.ml.model import AnomalyDetector


def train_and_save(rows) -> AnomalyDetector:
    """rows: list of feature vectors."""
    det = AnomalyDetector().fit(rows)
    det.save(inference.model_path())
    inference.set_detector(det)
    return det


def feature_rows_from_db(db) -> list[list[float]]:
    customers = {c.id: c for c in db.query(Customer).all()}
    groups = defaultdict(list)
    for t in db.query(Transaction).all():
        groups[t.customer_id].append(t)
    return [extract_features(t, customers[cid], [o for o in g if o is not t]) for cid, g in groups.items() for t in g]


if __name__ == "__main__":
    db = SessionLocal()
    rows = feature_rows_from_db(db)
    det = train_and_save(rows)
    print(f"trained on {len(rows)} transactions; flags {int(det.predict_is_anomaly(rows).sum())} as anomalous -> {inference.model_path()}")
