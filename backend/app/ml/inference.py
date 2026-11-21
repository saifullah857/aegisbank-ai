"""Shared, lazily-loaded detector. Returns None when no trained model exists — scoring then degrades
cleanly to the rule engine alone (deterministic fallback)."""
import os
from pathlib import Path

from app.ml.model import AnomalyDetector

_detector: AnomalyDetector | None = None
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "artifacts" / "isolation_forest.joblib"


def model_path() -> Path:
    return Path(os.environ.get("ML_MODEL_PATH") or DEFAULT_MODEL_PATH)


def get_detector() -> AnomalyDetector | None:
    global _detector
    if _detector is None and model_path().exists():
        _detector = AnomalyDetector.load(model_path())
    return _detector


def set_detector(detector: AnomalyDetector | None) -> None:
    global _detector
    _detector = detector


def reset() -> None:
    set_detector(None)
