"""
Avaliador de métricas para detecção de anomalias.

Calcula precisão, recall, F1, AUC-ROC e matriz de confusão quando temos
labels verdadeiros disponíveis (dataset sintético).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict

import numpy as np
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.logger import logger


@dataclass
class EvaluationMetrics:
    """Métricas agregadas de uma rodada de detecção."""

    method: str
    precision: float
    recall: float
    f1: float
    auc_roc: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    total: int
    anomalies_detected: int
    anomalies_true: int

    def to_dict(self) -> Dict:
        return asdict(self)


def avaliar(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    scores: np.ndarray,
    method: str = "unknown",
) -> EvaluationMetrics:
    """
    Avalia o desempenho do detector.

    Args:
        y_true: Labels verdadeiros (0=normal, 1=anomalia).
        y_pred: Labels previstos.
        scores: Scores contínuos (usados para AUC-ROC).
        method: Nome do método.

    Returns:
        Métricas consolidadas.
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)

    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    try:
        auc = float(roc_auc_score(y_true, scores))
    except ValueError:
        auc = float("nan")

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

    metrics = EvaluationMetrics(
        method=method,
        precision=precision,
        recall=recall,
        f1=f1,
        auc_roc=auc,
        true_positives=int(tp),
        false_positives=int(fp),
        true_negatives=int(tn),
        false_negatives=int(fn),
        total=int(len(y_true)),
        anomalies_detected=int(y_pred.sum()),
        anomalies_true=int(y_true.sum()),
    )

    logger.info("avaliacao_concluida", **metrics.to_dict())
    return metrics


def imprimir_relatorio(y_true: np.ndarray, y_pred: np.ndarray, method: str) -> str:
    """
    Retorna classification_report do sklearn como string.

    Args:
        y_true: Labels verdadeiros.
        y_pred: Labels previstos.
        method: Nome do método.

    Returns:
        Relatório formatado.
    """
    report = classification_report(
        y_true,
        y_pred,
        target_names=["normal", "anomalia"],
        zero_division=0,
    )
    header = f"\n{'='*60}\nRelatório - {method}\n{'='*60}\n"
    return header + report
