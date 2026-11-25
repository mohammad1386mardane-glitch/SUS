import csv
from pathlib import Path

import pytest

from app.ml_data import generate_samples, write_synthetic_dataset
from app.ml_features import FEATURE_NAMES, features_from_context
from app.rules.base import RuleContext


def test_generate_samples_is_reproducible_and_contains_both_labels() -> None:
    first = generate_samples(normal_count=20, suspicious_count=5, seed=7)
    second = generate_samples(normal_count=20, suspicious_count=5, seed=7)

    assert first == second
    assert len(first) == 25
    assert {sample.label for sample in first} == {0, 1}
    assert sum(sample.label == 0 for sample in first) == 20
    assert sum(sample.label == 1 for sample in first) == 5


def test_generate_samples_rejects_empty_class_counts() -> None:
    with pytest.raises(ValueError, match="must both be positive"):
        generate_samples(normal_count=0)


def test_write_synthetic_dataset_creates_numeric_csv_with_feature_schema(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "nested" / "events.csv"

    count = write_synthetic_dataset(
        output_path,
        normal_count=12,
        suspicious_count=3,
        seed=12,
    )

    with output_path.open(newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        rows = list(reader)

    assert count == len(rows) == 15
    assert reader.fieldnames == [*FEATURE_NAMES, "label"]
    assert {row["label"] for row in rows} == {"0", "1"}
    assert all(
        0.0 <= float(row[name]) <= 1.0
        for row in rows
        for name in FEATURE_NAMES
    )


def test_features_from_context_maps_optional_and_capped_signals() -> None:
    features = features_from_context(
        RuleContext(
            impossible_travel_speed_kmh=3600,
            consecutive_failures=5,
            distinct_users_per_ip=2,
            is_new_device=True,
            time_deviation_hours=None,
        )
    )

    assert features == {
        "travel_speed_ratio": 1.0,
        "consecutive_failures_ratio": 0.5,
        "distinct_users_per_ip_ratio": 0.2,
        "is_new_device": 1.0,
        "is_new_country": 0.0,
        "is_high_risk_ip": 0.0,
        "time_deviation_ratio": 0.0,
    }
