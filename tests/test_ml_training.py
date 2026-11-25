from pathlib import Path

import joblib
import pytest
from sklearn.ensemble import IsolationForest

from app.ml_data import write_synthetic_dataset
from app.ml_training import train_isolation_forest


def test_train_isolation_forest_uses_normal_rows_and_saves_model(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "events.csv"
    output_path = tmp_path / "artifacts" / "model.joblib"
    write_synthetic_dataset(
        input_path,
        normal_count=30,
        suspicious_count=8,
        seed=15,
    )

    summary = train_isolation_forest(
        input_path,
        output_path,
        random_state=9,
    )

    assert summary.normal_rows == 30
    assert summary.suspicious_rows == 8
    assert summary.output_path == tmp_path / "artifacts" / "model-v0001.joblib"
    assert summary.manifest_path == output_path.with_suffix(".json")
    assert summary.model_version == 1
    assert summary.random_state == 9
    assert isinstance(joblib.load(summary.output_path), IsolationForest)


@pytest.mark.parametrize("contamination", [0.0, 0.51])
def test_train_isolation_forest_rejects_invalid_contamination(
    tmp_path: Path,
    contamination: float,
) -> None:
    with pytest.raises(ValueError, match="contamination must be"):
        train_isolation_forest(
            tmp_path / "missing.csv",
            tmp_path / "model.joblib",
            contamination=contamination,
        )


def test_train_isolation_forest_rejects_invalid_feature_data(tmp_path: Path) -> None:
    input_path = tmp_path / "invalid.csv"
    input_path.write_text(
        "travel_speed_ratio,consecutive_failures_ratio,"
        "distinct_users_per_ip_ratio,is_new_device,is_new_country,"
        "is_high_risk_ip,time_deviation_ratio,label\n"
        "0,0,0,0,0,0,0,0\n"
        "0,0,0,0,0,0,0,0\n"
        "1.5,0,0,0,0,0,0,1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must be between 0 and 1"):
        train_isolation_forest(input_path, tmp_path / "model.joblib")
