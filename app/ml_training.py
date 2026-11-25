import csv
import math
import statistics
from dataclasses import dataclass
from pathlib import Path

from sklearn.ensemble import IsolationForest

from app.ml_features import FEATURE_NAMES
from app.model_registry import ModelRegistry

DEFAULT_CONTAMINATION = 0.05


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

    normal_features: list[list[float]] = []
    suspicious_count = 0
    expected_fields = [*FEATURE_NAMES, "label"]
    with input_path.open(newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames != expected_fields:
            raise ValueError(f"dataset columns must be exactly {expected_fields!r}")
        for line_number, row in enumerate(reader, start=2):
            label = row["label"]
            if label not in {"0", "1"}:
                raise ValueError(f"line {line_number}: label must be 0 or 1")
            feature_values = [
                _parse_feature(row[name], name, line_number) for name in FEATURE_NAMES
            ]
            if label == "0":
                normal_features.append(feature_values)
            else:
                suspicious_count += 1

    if len(normal_features) < 2:
        raise ValueError("dataset must contain at least two normal rows")
    if suspicious_count == 0:
        raise ValueError("dataset must contain at least one suspicious row")

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


def _parse_feature(value: str | None, name: str, line_number: int) -> float:
    if value is None:
        raise ValueError(f"line {line_number}: missing feature {name!r}")
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError(
            f"line {line_number}: feature {name!r} must be numeric"
        ) from error
    if not math.isfinite(parsed) or not 0 <= parsed <= 1:
        raise ValueError(
            f"line {line_number}: feature {name!r} must be between 0 and 1"
        )
    return parsed
