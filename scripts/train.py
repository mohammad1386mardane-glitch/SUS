import argparse
from pathlib import Path

from app.ml_training import DEFAULT_CONTAMINATION, train_isolation_forest
from app.settings import Settings


def main() -> None:
    settings = Settings()
    parser = argparse.ArgumentParser(
        description="Train an Isolation Forest on normal synthetic login features."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/synthetic-login-events.csv"),
    )
    parser.add_argument("--output", type=Path, default=settings.model_path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--contamination", type=float, default=DEFAULT_CONTAMINATION)
    arguments = parser.parse_args()

    summary = train_isolation_forest(
        arguments.input,
        arguments.output,
        random_state=arguments.seed,
        contamination=arguments.contamination,
    )
    print(
        f"Trained IsolationForest on {summary.normal_rows} normal rows "
        f"({summary.suspicious_rows} suspicious rows reserved) as version "
        f"{summary.model_version}: {summary.output_path} "
        f"(registry: {summary.manifest_path})"
    )


if __name__ == "__main__":
    main()
