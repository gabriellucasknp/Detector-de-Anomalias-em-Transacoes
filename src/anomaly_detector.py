"""
Detector de anomalias usando métodos do scikit-learn.

Implementa dois algoritmos clássicos:
- Isolation Forest (principal)
- DBSCAN + Z-Score (secundário, baseado em densidade)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest

from src.logger import logger


@dataclass
class DetectionResult:
    """Resultado de uma rodada de detecção."""

    scores: np.ndarray           # score contínuo (quanto maior, mais anômalo)
    labels: np.ndarray           # 1 = anomalia, 0 = normal
    method: str
    threshold: float


class IsolationForestDetector:
    """Detector baseado em Isolation Forest (scikit-learn)."""

    def __init__(
        self,
        contamination: float = 0.03,
        n_estimators: int = 100,
        random_state: int = 42,
    ) -> None:
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1,
        )

    def fit_predict(self, X: np.ndarray) -> DetectionResult:
        """Treina e detecta anomalias."""
        logger.info(
            "isolation_forest_iniciando",
            shape=X.shape,
            contamination=self.contamination,
        )
        self.model.fit(X)
        # decision_function: quanto MENOR, mais anômalo → invertemos para score positivo
        raw_scores = -self.model.decision_function(X)
        preds = self.model.predict(X)  # -1 anomalia, 1 normal
        labels = (preds == -1).astype(int)

        threshold = float(np.percentile(raw_scores, 100 * (1 - self.contamination)))

        logger.info(
            "isolation_forest_concluido",
            anomalias=int(labels.sum()),
            threshold=threshold,
        )
        return DetectionResult(
            scores=raw_scores,
            labels=labels,
            method="isolation_forest",
            threshold=threshold,
        )


class DBSCANDetector:
    """Detector baseado em DBSCAN + Z-Score para validação cruzada."""

    def __init__(
        self,
        eps: float = 0.5,
        min_samples: int = 5,
        zscore_threshold: float = 3.0,
    ) -> None:
        self.eps = eps
        self.min_samples = min_samples
        self.zscore_threshold = zscore_threshold

    def fit_predict(self, X: np.ndarray) -> DetectionResult:
        """Detecta anomalias combinando DBSCAN e Z-Score."""
        logger.info("dbscan_iniciando", shape=X.shape, eps=self.eps)

        # DBSCAN: pontos com label -1 são ruído (potenciais anomalias)
        db = DBSCAN(eps=self.eps, min_samples=self.min_samples, n_jobs=-1)
        cluster_labels = db.fit_predict(X)
        dbscan_anomalies = (cluster_labels == -1).astype(int)

        # Z-Score nas features: se qualquer feature tem |z| > threshold → anomalia
        means = X.mean(axis=0)
        stds = X.std(axis=0) + 1e-9
        zscores = np.abs((X - means) / stds)
        zscore_anomalies = (zscores.max(axis=1) > self.zscore_threshold).astype(int)

        # Combinação: é anomalia se DBSCAN OU Z-Score indicar
        labels = ((dbscan_anomalies == 1) | (zscore_anomalies == 1)).astype(int)

        # Score contínuo = máximo z-score (interpretável)
        scores = zscores.max(axis=1)

        logger.info(
            "dbscan_concluido",
            anomalias=int(labels.sum()),
            dbscan_only=int(dbscan_anomalies.sum()),
            zscore_only=int(zscore_anomalies.sum()),
        )
        return DetectionResult(
            scores=scores,
            labels=labels,
            method="dbscan_zscore",
            threshold=self.zscore_threshold,
        )


def detectar_anomalias_combinado(
    X: np.ndarray,
    contamination: float = 0.03,
) -> Tuple[DetectionResult, DetectionResult]:
    """
    Roda ambos os detectores e retorna os resultados.

    Args:
        X: Matriz de features já pré-processada.
        contamination: Taxa esperada de anomalias.

    Returns:
        Tupla (resultado_iforest, resultado_dbscan).
    """
    iforest = IsolationForestDetector(contamination=contamination)
    dbscan = DBSCANDetector(eps=0.8, min_samples=5, zscore_threshold=3.0)

    r_iforest = iforest.fit_predict(X)
    r_dbscan = dbscan.fit_predict(X)
    return r_iforest, r_dbscan


def montar_df_anomalias(
    df_features: pd.DataFrame,
    resultado: DetectionResult,
) -> pd.DataFrame:
    """
    Monta DataFrame pronto para persistir em `anomalias`.

    Args:
        df_features: DataFrame com as transações (precisa ter 'id' ou 'transacao_id').
        resultado: Resultado da detecção.

    Returns:
        DataFrame com colunas compatíveis com a tabela `anomalias`.
    """
    # Identifica coluna de ID da transação
    if "transacao_id" in df_features.columns:
        ids = df_features["transacao_id"].values
    elif "id" in df_features.columns:
        ids = df_features["id"].values
    else:
        # Sem ID do banco: gera sequência (modo offline/CSV)
        ids = np.arange(1, len(df_features) + 1)

    return pd.DataFrame({
        "transacao_id": ids.astype(int),
        "cliente_id": df_features["cliente_id"].values.astype(int),
        "score_anomalia": resultado.scores.astype(float).round(6),
        "metodo_deteccao": resultado.method,
        "is_anomaly": resultado.labels.astype(bool),
    })
