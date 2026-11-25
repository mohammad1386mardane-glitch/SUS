import argparse
from pathlib import Path

from app.ml_data import DEFAULT_SEED, write_synthetic_dataset


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic login features for model training."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/synthetic-login-events.csv"),
    )
    parser.add_argument("--normal-count", type=int, default=1000)
    parser.add_argument("--suspicious-count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    arguments = parser.parse_args()

    count = write_synthetic_dataset(
        arguments.output,
        normal_count=arguments.normal_count,
        suspicious_count=arguments.suspicious_count,
        seed=arguments.seed,
    )
    print(f"Wrote {count} synthetic events to {arguments.output}")


if __name__ == "__main__":
    main()
