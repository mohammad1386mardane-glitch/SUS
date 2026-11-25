import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
from sklearn.ensemble import IsolationForest

from app.ml_features import FEATURE_NAMES, features_from_context
from app.model_registry import ModelRegistry
from app.rules.base import RuleContext

_MODEL_TYPE = "sklearn.ensemble.IsolationForest"


@dataclass(frozen=True, slots=True)
class InferenceResult:
    risk_score: int
    is_anomaly: bool
    decision_function: float
    model_version: int


class InferenceService:
    def __init__(self, model_base_path: Path) -> None:
        self._registry = ModelRegistry(model_base_path)

    def score(self, context: RuleContext) -> InferenceResult:
        registered = self._registry.latest()
        if registered is None:
            raise FileNotFoundError(
                f"no trained model is registered at {self._registry.manifest_path}"
            )
        if registered.metadata.model_type != _MODEL_TYPE:
            raise ValueError(
                f"unsupported registered model type: {registered.metadata.model_type}"
            )
        if registered.metadata.feature_names != FEATURE_NAMES:
            raise ValueError(
                "registered model features do not match the current schema"
            )

        model = _load_model(registered.artifact_path)
        features = features_from_context(context)
        values = [features[name] for name in registered.metadata.feature_names]
        decisions = model.decision_function([values])
        if len(decisions) != 1:
            raise RuntimeError("model returned an unexpected number of scores")
        decision_value = float(decisions[0])
        if not math.isfinite(decision_value):
            raise ValueError("model returned a non-finite decision score")

        risk_score = _decision_to_risk_score(
            decision_value,
            registered.metadata.calibration_scale,
        )
        return InferenceResult(
            risk_score=risk_score,
            is_anomaly=decision_value < 0,
            decision_function=decision_value,
            model_version=registered.metadata.version,
        )


@lru_cache(maxsize=8)
def _load_model(artifact_path: Path) -> IsolationForest:
    model = joblib.load(artifact_path)
    if not isinstance(model, IsolationForest):
        raise TypeError("registered artifact is not an IsolationForest model")
    return model


def _decision_to_risk_score(decision_value: float, calibration_scale: float) -> int:
    if not math.isfinite(decision_value):
        raise ValueError("decision_value must be finite")
    if not math.isfinite(calibration_scale) or calibration_scale <= 0:
        raise ValueError("calibration_scale must be finite and greater than 0")

    scaled_value = decision_value / calibration_scale
    if scaled_value >= 0:
        probability = math.exp(-scaled_value) / (1 + math.exp(-scaled_value))
    else:
        probability = 1 / (1 + math.exp(scaled_value))
    return max(0, min(100, round(100 * probability)))
