import math
import statistics
from dataclasses import dataclass
from pathlib import Path

from sklearn.ensemble import IsolationForest

from app.ml_data import load_labeled_dataset
from app.model_registry import ModelRegistry

DEFAULT_CONTAMINATION = 0.02


@dataclass(frozen=True, slots=True)
class TrainingSummary:
    normal_rows: int
    suspicious_rows: int
    output_path: Path
    manifest_path: Path
    model_version: int
    random_state: int
    contamination: float


def train_isolation_forest(
    input_path: Path,
    output_path: Path,
    *,
    random_state: int = 42,
    contamination: float = DEFAULT_CONTAMINATION,
) -> TrainingSummary:
    if not 0 < contamination <= 0.5:
        raise ValueError("contamination must be greater than 0 and at most 0.5")

    dataset = load_labeled_dataset(input_path)
    normal_features = [
        list(values)
        for values, label in zip(dataset.features, dataset.labels, strict=True)
        if label == 0
    ]
    suspicious_count = dataset.labels.count(1)

    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=random_state,
        n_jobs=1,
    )
    model.fit(normal_features)
    normal_margin = statistics.median(
        float(value) for value in model.decision_function(normal_features)
    )
    if not math.isfinite(normal_margin) or normal_margin <= 0:
        raise ValueError(
            "normal training decision margin must be positive for score calibration"
        )
    calibration_scale = normal_margin / math.log(19)

    registry = ModelRegistry(output_path)
    registered_model = registry.register(
        model,
        model_type="sklearn.ensemble.IsolationForest",
        normal_rows=len(normal_features),
        suspicious_rows=suspicious_count,
        random_state=random_state,
        contamination=contamination,
        calibration_scale=calibration_scale,
    )
    return TrainingSummary(
        normal_rows=len(normal_features),
        suspicious_rows=suspicious_count,
        output_path=registered_model.artifact_path,
        manifest_path=registry.manifest_path,
        model_version=registered_model.metadata.version,
        random_state=random_state,
        contamination=contamination,
    )
