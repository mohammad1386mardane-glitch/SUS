import csv
import math
import random
from dataclasses import dataclass, replace
from pathlib import Path

from app.ml_features import FEATURE_NAMES, features_from_context
from app.rules.base import RuleContext

DEFAULT_SEED = 42


@dataclass(frozen=True, slots=True)
class SyntheticSample:
    context: RuleContext
    label: int

    def as_row(self) -> dict[str, int | float]:
        return {
            **features_from_context(self.context),
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class LabeledDataset:
    features: tuple[tuple[float, ...], ...]
    labels: tuple[int, ...]


def generate_samples(
    *,
    normal_count: int = 1000,
    suspicious_count: int = 100,
    seed: int = DEFAULT_SEED,
) -> list[SyntheticSample]:
    if normal_count < 1 or suspicious_count < 1:
        raise ValueError("normal_count and suspicious_count must both be positive")

    rng = random.Random(seed)
    samples = [SyntheticSample(_normal_context(rng), 0) for _ in range(normal_count)]
    samples.extend(
        SyntheticSample(_suspicious_context(rng), 1) for _ in range(suspicious_count)
    )
    rng.shuffle(samples)
    return samples


def load_labeled_dataset(input_path: Path) -> LabeledDataset:
    feature_rows: list[tuple[float, ...]] = []
    labels: list[int] = []
    expected_fields = [*FEATURE_NAMES, "label"]
    with input_path.open(newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames != expected_fields:
            raise ValueError(f"dataset columns must be exactly {expected_fields!r}")
        for line_number, row in enumerate(reader, start=2):
            label = row["label"]
            if label not in {"0", "1"}:
                raise ValueError(f"line {line_number}: label must be 0 or 1")
            feature_rows.append(
                tuple(
                    _parse_feature(row[name], name, line_number)
                    for name in FEATURE_NAMES
                )
            )
            labels.append(int(label))

    if labels.count(0) < 2:
        raise ValueError("dataset must contain at least two normal rows")
    if labels.count(1) == 0:
        raise ValueError("dataset must contain at least one suspicious row")
    return LabeledDataset(tuple(feature_rows), tuple(labels))


def write_synthetic_dataset(
    output_path: Path,
    *,
    normal_count: int = 1000,
    suspicious_count: int = 100,
    seed: int = DEFAULT_SEED,
) -> int:
    samples = generate_samples(
        normal_count=normal_count,
        suspicious_count=suspicious_count,
        seed=seed,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=[*FEATURE_NAMES, "label"])
        writer.writeheader()
        writer.writerows(sample.as_row() for sample in samples)
    return len(samples)


def _normal_context(rng: random.Random) -> RuleContext:
    is_new_device = rng.random() < 0.08
    is_new_country = rng.random() < 0.02 and not is_new_device
    return RuleContext(
        impossible_travel_speed_kmh=min(rng.expovariate(1 / 120), 850),
        consecutive_failures=int(rng.random() < 0.03),
        distinct_users_per_ip=2 if rng.random() < 0.02 else 1,
        is_new_device=is_new_device,
        is_new_country=is_new_country,
        time_deviation_hours=rng.randint(0, 5),
    )


def _suspicious_context(rng: random.Random) -> RuleContext:
    context = _normal_context(rng)
    attack_type = rng.choice(
        (
            "impossible_travel",
            "brute_force",
            "credential_stuffing",
            "new_device_and_country",
            "high_risk_ip",
            "unusual_hour",
            "subthreshold_combination",
        )
    )
    if attack_type == "impossible_travel":
        return replace(context, impossible_travel_speed_kmh=rng.uniform(901, 2200))
    if attack_type == "brute_force":
        return replace(context, consecutive_failures=rng.randint(5, 10))
    if attack_type == "credential_stuffing":
        distinct_identities = rng.randint(5, 10)
        return replace(
            context,
            distinct_users_per_ip=distinct_identities,
            distinct_failed_users_per_ip=distinct_identities,
            distinct_failed_devices_per_ip=distinct_identities,
        )
    if attack_type == "new_device_and_country":
        return replace(context, is_new_device=True, is_new_country=True)
    if attack_type == "high_risk_ip":
        return replace(context, is_high_risk_ip=True)
    if attack_type == "unusual_hour":
        return replace(context, time_deviation_hours=rng.randint(6, 12))
    return replace(
        context,
        impossible_travel_speed_kmh=rng.uniform(600, 900),
        consecutive_failures=rng.randint(2, 4),
        distinct_users_per_ip=rng.randint(3, 4),
        distinct_failed_users_per_ip=rng.randint(3, 4),
        distinct_failed_devices_per_ip=rng.randint(3, 4),
        is_new_device=True,
        is_new_country=False,
        time_deviation_hours=rng.randint(3, 5),
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
