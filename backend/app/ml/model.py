"""Isolation Forest anomaly detector. Scores are normalized so 0.0 = normal, 1.0 = highly anomalous."""
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class AnomalyDetector:
    def __init__(self, contamination: float = 0.03, random_state: int = 42, n_estimators: int = 200):
        self.pipeline = Pipeline([("scale", StandardScaler()),
                                  ("forest", IsolationForest(n_estimators=n_estimators, contamination=contamination, random_state=random_state))])
        self._lo = self._hi = None
        self._fitted = False

    def fit(self, X):
        X = np.array(X, dtype=float)
        self.pipeline.fit(X)
        raw = -self.pipeline.decision_function(X)
        self._lo, self._hi, self._fitted = float(raw.min()), float(raw.max()), True
        return self

    def _need(self):
        if not self._fitted:
            raise RuntimeError("AnomalyDetector must be fit() or load()ed first")

    def normalized_scores(self, X) -> np.ndarray:
        self._need()
        raw = -self.pipeline.decision_function(np.array(X, dtype=float))
        return np.clip((raw - self._lo) / ((self._hi - self._lo) or 1e-9), 0.0, 1.0)

    def predict_is_anomaly(self, X) -> np.ndarray:
        self._need()
        return self.pipeline.predict(np.array(X, dtype=float)) == -1

    def score_one(self, features) -> dict:
        return {"anomaly_score": round(float(self.normalized_scores([features])[0]), 4),
                "is_anomaly": bool(self.predict_is_anomaly([features])[0])}

    def save(self, path: Path):
        self._need()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"pipeline": self.pipeline, "lo": self._lo, "hi": self._hi}, path)

    @classmethod
    def load(cls, path: Path) -> "AnomalyDetector":
        d = joblib.load(path)
        det = cls()
        det.pipeline, det._lo, det._hi, det._fitted = d["pipeline"], d["lo"], d["hi"], True
        return det
