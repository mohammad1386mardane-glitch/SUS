from dataclasses import dataclass
from pathlib import Path

from sklearn.metrics import precision_score, recall_score, roc_auc_score

from app.ml_data import load_labeled_dataset
from app.ml_features import FEATURE_NAMES
from app.ml_inference import InferenceService


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    precision: float
    recall: float
    roc_auc: float
    false_positive_rate: float
    sample_count: int
    model_version: int


def evaluate_model(
    input_path: Path,
    model_base_path: Path,
) -> EvaluationMetrics:
    dataset = load_labeled_dataset(input_path)
    service = InferenceService(model_base_path)
    feature_rows = [
        dict(zip(FEATURE_NAMES, values, strict=True)) for values in dataset.features
    ]
    results = [service.score_features(row) for row in feature_rows]
    predictions = [int(result.is_anomaly) for result in results]
    scores = [result.risk_score for result in results]
    false_positive_count = sum(
        label == 0 and prediction == 1
        for label, prediction in zip(dataset.labels, predictions, strict=True)
    )
    normal_count = dataset.labels.count(0)

    return EvaluationMetrics(
        precision=float(precision_score(dataset.labels, predictions, zero_division=0)),
        recall=float(recall_score(dataset.labels, predictions, zero_division=0)),
        roc_auc=float(roc_auc_score(dataset.labels, scores)),
        false_positive_rate=false_positive_count / normal_count,
        sample_count=len(dataset.labels),
        model_version=results[0].model_version,
    )
