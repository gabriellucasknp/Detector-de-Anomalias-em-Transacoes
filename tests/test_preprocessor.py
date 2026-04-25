"""Testes unitários do TransactionPreprocessor."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.preprocessor import TransactionPreprocessor


def test_preprocessor_fit_transform_retorna_features(df_transacoes_sample):
    """Verifica que fit_transform retorna DataFrame + matriz X."""
    pre = TransactionPreprocessor()
    df_feat, X = pre.fit_transform(df_transacoes_sample)

    assert isinstance(df_feat, pd.DataFrame)
    assert isinstance(X, np.ndarray)
    assert X.shape[0] == len(df_transacoes_sample)
    assert X.shape[1] == len(pre.feature_columns)


def test_preprocessor_gera_features_esperadas(df_transacoes_sample):
    """Verifica presença de todas as features esperadas."""
    pre = TransactionPreprocessor()
    df_feat, _ = pre.fit_transform(df_transacoes_sample)

    esperadas = [
        "valor_log", "hora", "dia_semana", "is_madrugada", "is_fim_semana",
        "frequencia_cliente", "valor_medio_cliente", "valor_std_cliente",
        "desvio_valor_cliente", "tipo_transacao_encoded",
        "local_encoded", "dispositivo_encoded",
    ]
    for col in esperadas:
        assert col in df_feat.columns, f"Coluna ausente: {col}"


def test_preprocessor_transform_sem_fit_falha(df_transacoes_sample):
    """transform() sem fit prévio deve levantar erro."""
    pre = TransactionPreprocessor()
    with pytest.raises(RuntimeError):
        pre.transform(df_transacoes_sample)


def test_preprocessor_transform_apos_fit(df_transacoes_sample):
    """transform() funciona após fit_transform."""
    pre = TransactionPreprocessor()
    pre.fit_transform(df_transacoes_sample)

    # Usa metade como "novos dados"
    novos = df_transacoes_sample.head(50).copy()
    df_feat, X = pre.transform(novos)
    assert X.shape[0] == 50
    assert X.shape[1] == len(pre.feature_columns)


def test_valor_log_sem_negativos_nem_nan(df_transacoes_sample):
    """valor_log deve ser finito e não-negativo."""
    pre = TransactionPreprocessor()
    df_feat, _ = pre.fit_transform(df_transacoes_sample)

    assert df_feat["valor_log"].notna().all()
    assert (df_feat["valor_log"] >= 0).all()


def test_is_madrugada_binario(df_transacoes_sample):
    """is_madrugada deve ser 0 ou 1."""
    pre = TransactionPreprocessor()
    df_feat, _ = pre.fit_transform(df_transacoes_sample)

    assert set(df_feat["is_madrugada"].unique()).issubset({0, 1})
