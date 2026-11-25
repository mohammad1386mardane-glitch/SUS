import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.ml_evaluation import evaluate_model
from app.settings import Settings


def main() -> None:
    settings = Settings()
    parser = argparse.ArgumentParser(
        description="Evaluate the registered model against labeled login features."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/synthetic-login-events.csv"),
    )
    parser.add_argument("--model-path", type=Path, default=settings.model_path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    metrics = evaluate_model(arguments.input, arguments.model_path)
    report = json.dumps(asdict(metrics), indent=2)
    print(report)
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(f"{report}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
