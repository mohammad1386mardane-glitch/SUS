from pathlib import Path

from app.ml_data import write_synthetic_dataset
from app.ml_evaluation import evaluate_model
from app.ml_training import train_isolation_forest


def test_evaluate_model_returns_precision_recall_and_roc_auc(
    tmp_path: Path,
) -> None:
    training_data = tmp_path / "training.csv"
    evaluation_data = tmp_path / "evaluation.csv"
    model_base_path = tmp_path / "artifacts" / "model.joblib"
    write_synthetic_dataset(
        training_data,
        normal_count=1000,
        suspicious_count=200,
        seed=31,
    )
    write_synthetic_dataset(
        evaluation_data,
        normal_count=500,
        suspicious_count=100,
        seed=32,
    )
    train_isolation_forest(training_data, model_base_path, random_state=42)

    metrics = evaluate_model(evaluation_data, model_base_path)

    assert 0.0 <= metrics.precision <= 1.0
    assert 0.0 <= metrics.recall <= 1.0
    assert 0.0 <= metrics.roc_auc <= 1.0
    assert metrics.false_positive_rate < 0.02
    assert metrics.sample_count == 600
    assert metrics.model_version == 1
