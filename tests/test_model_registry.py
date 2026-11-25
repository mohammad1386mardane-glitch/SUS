import json
from pathlib import Path

import pytest

from app.ml_features import FEATURE_NAMES
from app.model_registry import ModelRegistry


def test_registry_saves_versioned_artifacts_and_latest_metadata(
    tmp_path: Path,
) -> None:
    registry = ModelRegistry(tmp_path / "model.joblib")

    first = registry.register(
        {"model": 1},
        model_type="TestEstimator",
        normal_rows=20,
        suspicious_rows=5,
        random_state=42,
        contamination=0.05,
    )
    second = registry.register(
        {"model": 2},
        model_type="TestEstimator",
        normal_rows=30,
        suspicious_rows=7,
        random_state=9,
        contamination=0.1,
    )
    latest = registry.latest()

    assert first.artifact_path.name == "model-v0001.joblib"
    assert first.metadata_path.name == "model-v0001.json"
    assert second.artifact_path.name == "model-v0002.joblib"
    assert second.metadata.version == 2
    assert latest == second
    assert latest is not None
    assert latest.metadata.feature_names == FEATURE_NAMES
    assert latest.metadata.normal_rows == 30
    assert latest.metadata.created_at.utcoffset() is not None
    assert registry.manifest_path.is_file()
    assert json.loads(registry.manifest_path.read_text(encoding="utf-8")) == {
        "version": 2,
        "artifact": "model-v0002.joblib",
    }


def test_registry_rejects_manifest_artifact_path_mismatch(tmp_path: Path) -> None:
    registry = ModelRegistry(tmp_path / "model.joblib")
    registry.register(
        {"model": 1},
        model_type="TestEstimator",
        normal_rows=20,
        suspicious_rows=5,
        random_state=42,
        contamination=0.05,
    )
    registry.manifest_path.write_text(
        json.dumps({"version": 1, "artifact": "..\\outside.joblib"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="artifact name does not match"):
        registry.latest()


def test_registry_surfaces_missing_registered_artifact(tmp_path: Path) -> None:
    registry = ModelRegistry(tmp_path / "model.joblib")
    registered = registry.register(
        {"model": 1},
        model_type="TestEstimator",
        normal_rows=20,
        suspicious_rows=5,
        random_state=42,
        contamination=0.05,
    )
    registered.artifact_path.unlink()

    with pytest.raises(FileNotFoundError, match="registered model artifact is missing"):
        registry.latest()
