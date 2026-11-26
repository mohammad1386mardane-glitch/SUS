import math
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
from sklearn.ensemble import IsolationForest

from app.ml_features import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    features_from_context,
)
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
        return self.score_features(features_from_context(context))

    def score_features(self, features: Mapping[str, float]) -> InferenceResult:
        registered = self._registry.latest()
        if registered is None:
            raise FileNotFoundError(
                f"no trained model is registered at {self._registry.manifest_path}"
            )
        if registered.metadata.model_type != _MODEL_TYPE:
            raise ValueError(
                f"unsupported registered model type: {registered.metadata.model_type}"
            )
        if registered.metadata.feature_schema_version != FEATURE_SCHEMA_VERSION:
            raise ValueError(
                "registered model feature schema version "
                f"{registered.metadata.feature_schema_version} does not match "
                f"current version {FEATURE_SCHEMA_VERSION}"
            )
        if registered.metadata.feature_names != FEATURE_NAMES:
            raise ValueError(
                "registered model features do not match the current schema"
            )

        if set(features) != set(FEATURE_NAMES):
            raise ValueError("inference features do not match the current schema")
        values: list[float] = []
        for name in FEATURE_NAMES:
            value = features[name]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                raise ValueError(f"inference feature {name!r} must be between 0 and 1")
            values.append(float(value))

        model = _load_model(registered.artifact_path)
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
