"""Testes unitários dos detectores de anomalias."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.anomaly_detector import (
    DBSCANDetector,
    DetectionResult,
    IsolationForestDetector,
    detectar_anomalias_combinado,
    montar_df_anomalias,
)
from src.evaluator import avaliar
from src.preprocessor import TransactionPreprocessor


def test_isolation_forest_retorna_detection_result(df_transacoes_sample):
    pre = TransactionPreprocessor()
    _, X = pre.fit_transform(df_transacoes_sample)

    detector = IsolationForestDetector(contamination=0.1)
    result = detector.fit_predict(X)

    assert isinstance(result, DetectionResult)
    assert result.method == "isolation_forest"
    assert len(result.labels) == len(X)
    assert len(result.scores) == len(X)
    assert set(np.unique(result.labels)).issubset({0, 1})


def test_dbscan_retorna_detection_result(df_transacoes_sample):
    pre = TransactionPreprocessor()
    _, X = pre.fit_transform(df_transacoes_sample)

    detector = DBSCANDetector(eps=0.8, min_samples=5, zscore_threshold=2.5)
    result = detector.fit_predict(X)

    assert isinstance(result, DetectionResult)
    assert result.method == "dbscan_zscore"
    assert len(result.labels) == len(X)


def test_isolation_forest_detecta_anomalias_conhecidas(df_transacoes_sample):
    """Com labels verdadeiros, o IForest deve ter recall > 0.3."""
    pre = TransactionPreprocessor()
    df_feat, X = pre.fit_transform(df_transacoes_sample)

    detector = IsolationForestDetector(contamination=0.1)
    result = detector.fit_predict(X)

    y_true = df_feat["is_anomaly_true"].values
    metrics = avaliar(y_true, result.labels, result.scores, "iforest_test")

    # Em um dataset com anomalias claras, esperamos recall decente
    assert metrics.recall > 0.3, f"Recall muito baixo: {metrics.recall}"


def test_deteccao_combinada(df_transacoes_sample):
    """Testa a função de conveniência que roda os dois detectores."""
    pre = TransactionPreprocessor()
    _, X = pre.fit_transform(df_transacoes_sample)

    r_if, r_db = detectar_anomalias_combinado(X, contamination=0.1)
    assert r_if.method == "isolation_forest"
    assert r_db.method == "dbscan_zscore"


def test_montar_df_anomalias(df_transacoes_sample):
    """Verifica estrutura do DataFrame de anomalias."""
    pre = TransactionPreprocessor()
    df_feat, X = pre.fit_transform(df_transacoes_sample)

    detector = IsolationForestDetector(contamination=0.1)
    result = detector.fit_predict(X)

    df_anom = montar_df_anomalias(df_feat, result)

    cols_esperadas = {
        "transacao_id", "cliente_id", "score_anomalia",
        "metodo_deteccao", "is_anomaly",
    }
    assert cols_esperadas.issubset(df_anom.columns)
    assert len(df_anom) == len(df_feat)
    assert df_anom["metodo_deteccao"].unique().tolist() == ["isolation_forest"]


def test_avaliador_metricas_validas(df_transacoes_sample):
    """Todas as métricas devem estar no intervalo [0, 1]."""
    pre = TransactionPreprocessor()
    df_feat, X = pre.fit_transform(df_transacoes_sample)

    detector = IsolationForestDetector(contamination=0.1)
    result = detector.fit_predict(X)

    y_true = df_feat["is_anomaly_true"].values
    m = avaliar(y_true, result.labels, result.scores, "test")

    assert 0.0 <= m.precision <= 1.0
    assert 0.0 <= m.recall <= 1.0
    assert 0.0 <= m.f1 <= 1.0
    assert m.total == len(y_true)
    assert m.true_positives + m.false_positives == m.anomalies_detected
    assert m.true_positives + m.false_negatives == m.anomalies_true


def test_contamination_fora_do_intervalo_levanta_erro():
    """sklearn levanta erro se contamination > 0.5."""
    with pytest.raises(ValueError):
        IsolationForestDetector(contamination=1.5).fit_predict(np.random.rand(100, 5))


def test_pipeline_end_to_end_minimo(df_transacoes_sample):
    """Sanity check: pipeline rodando de ponta a ponta com amostra."""
    pre = TransactionPreprocessor()
    df_feat, X = pre.fit_transform(df_transacoes_sample)

    r_if, r_db = detectar_anomalias_combinado(X, contamination=0.1)
    df_anom_if = montar_df_anomalias(df_feat, r_if)
    df_anom_db = montar_df_anomalias(df_feat, r_db)

    assert len(df_anom_if) == len(df_transacoes_sample)
    assert len(df_anom_db) == len(df_transacoes_sample)
    assert df_anom_if["is_anomaly"].sum() > 0
