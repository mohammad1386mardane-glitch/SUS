import json
from pathlib import Path

import pytest

from app.ml_data import write_synthetic_dataset
from app.ml_features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION
from app.ml_inference import InferenceService
from app.ml_training import train_isolation_forest
from app.model_registry import ModelRegistry
from app.rules.base import RuleContext


def test_inference_returns_bounded_score_for_normal_and_anomalous_contexts(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "events.csv"
    model_base_path = tmp_path / "model.joblib"
    write_synthetic_dataset(
        input_path,
        normal_count=100,
        suspicious_count=30,
        seed=31,
    )
    train_isolation_forest(input_path, model_base_path, random_state=31)
    service = InferenceService(model_base_path)
    registered_model = ModelRegistry(model_base_path).latest()

    normal = service.score(
        RuleContext(
            impossible_travel_speed_kmh=50,
            distinct_users_per_ip=1,
            time_deviation_hours=1,
        )
    )
    anomalous = service.score(RuleContext(is_high_risk_ip=True))

    assert normal.model_version == anomalous.model_version == 1
    assert registered_model is not None
    assert registered_model.metadata.feature_schema_version == FEATURE_SCHEMA_VERSION
    assert 0 <= normal.risk_score <= 100
    assert 0 <= anomalous.risk_score <= 100
    assert normal.is_anomaly == (normal.decision_function < 0)
    assert anomalous.is_anomaly == (anomalous.decision_function < 0)
    if normal.is_anomaly:
        assert normal.risk_score >= 50
    else:
        assert normal.risk_score <= 50
    if anomalous.is_anomaly:
        assert anomalous.risk_score >= 50
    else:
        assert anomalous.risk_score <= 50


def test_inference_fails_explicitly_when_no_model_is_registered(
    tmp_path: Path,
) -> None:
    service = InferenceService(tmp_path / "missing-model.joblib")

    with pytest.raises(FileNotFoundError, match="no trained model is registered"):
        service.score(RuleContext())


def test_inference_rejects_artifacts_with_a_different_feature_schema(
    tmp_path: Path,
) -> None:
    model_base_path = tmp_path / "model.joblib"
    ModelRegistry(model_base_path).register(
        {"not": "an IsolationForest"},
        model_type="sklearn.ensemble.IsolationForest",
        normal_rows=20,
        suspicious_rows=5,
        random_state=42,
        contamination=0.05,
        calibration_scale=0.05,
        feature_names=tuple(reversed(FEATURE_NAMES)),
    )

    with pytest.raises(ValueError, match="features do not match"):
        InferenceService(model_base_path).score(RuleContext())


def test_inference_rejects_legacy_model_metadata_without_schema_version(
    tmp_path: Path,
) -> None:
    model_base_path = tmp_path / "legacy-model.joblib"
    registered = ModelRegistry(model_base_path).register(
        {"not": "an IsolationForest"},
        model_type="sklearn.ensemble.IsolationForest",
        normal_rows=20,
        suspicious_rows=5,
        random_state=42,
        contamination=0.05,
        calibration_scale=0.05,
    )
    metadata = json.loads(registered.metadata_path.read_text(encoding="utf-8"))
    metadata.pop("feature_schema_version")
    registered.metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    legacy = ModelRegistry(model_base_path).latest()

    assert legacy is not None
    assert legacy.metadata.feature_schema_version == 1
    with pytest.raises(ValueError, match="schema version 1 does not match current"):
        InferenceService(model_base_path).score(RuleContext())


def test_inference_rejects_incompatible_feature_schema_version(
    tmp_path: Path,
) -> None:
    model_base_path = tmp_path / "future-model.joblib"
    ModelRegistry(model_base_path).register(
        {"not": "an IsolationForest"},
        model_type="sklearn.ensemble.IsolationForest",
        normal_rows=20,
        suspicious_rows=5,
        random_state=42,
        contamination=0.05,
        calibration_scale=0.05,
        feature_schema_version=FEATURE_SCHEMA_VERSION + 1,
    )

    with pytest.raises(ValueError, match="does not match current version"):
        InferenceService(model_base_path).score(RuleContext())
