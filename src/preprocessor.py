"""
Módulo de pré-processamento e feature engineering.

Transforma transações brutas em features numéricas úteis para os modelos
de detecção de anomalias.
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler

from src.logger import logger


class TransactionPreprocessor:
    """
    Pré-processador de transações.

    Gera features como:
    - valor_log: log do valor (reduz cauda longa)
    - valor_normalizado: z-score do valor
    - hora: hora do dia
    - dia_semana: dia da semana (0-6)
    - frequencia_cliente: nº de transações do cliente
    - valor_medio_cliente: valor médio histórico do cliente
    - desvio_valor_cliente: desvio do valor atual em relação à média do cliente
    - is_madrugada: flag para transações entre 0h-6h
    - tipo_encoded, local_encoded, dispositivo_encoded: categorias encodadas
    """

    def __init__(self) -> None:
        self.scaler = StandardScaler()
        self.encoders: dict[str, LabelEncoder] = {}
        self.feature_columns: List[str] = []
        self._fitted = False

    def _criar_features_temporais(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extrai features de data/hora."""
        df = df.copy()
        df["data_transacao"] = pd.to_datetime(df["data_transacao"])
        df["hora"] = df["data_transacao"].dt.hour
        df["dia_semana"] = df["data_transacao"].dt.dayofweek
        df["is_madrugada"] = ((df["hora"] >= 0) & (df["hora"] <= 6)).astype(int)
        df["is_fim_semana"] = (df["dia_semana"] >= 5).astype(int)
        return df

    def _criar_features_valor(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features relacionadas ao valor."""
        df = df.copy()
        df["valor"] = df["valor"].astype(float)
        # log1p para lidar com valores muito grandes e evitar log(0)
        df["valor_log"] = np.log1p(df["valor"])
        return df

    def _criar_features_cliente(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features agregadas por cliente (comportamento histórico)."""
        df = df.copy()

        agg = df.groupby("cliente_id").agg(
            frequencia_cliente=("valor", "count"),
            valor_medio_cliente=("valor", "mean"),
            valor_std_cliente=("valor", "std"),
        ).reset_index()
        agg["valor_std_cliente"] = agg["valor_std_cliente"].fillna(0)

        df = df.merge(agg, on="cliente_id", how="left")

        # Desvio do valor atual vs média histórica do cliente
        df["desvio_valor_cliente"] = (
            (df["valor"] - df["valor_medio_cliente"])
            / (df["valor_std_cliente"] + 1e-6)
        )
        return df

    def _encodar_categoricas(
        self, df: pd.DataFrame, fit: bool = True
    ) -> pd.DataFrame:
        """Converte colunas categóricas em numéricas via LabelEncoder."""
        df = df.copy()
        categoricas = ["tipo_transacao", "local", "dispositivo"]

        for col in categoricas:
            if col not in df.columns:
                continue
            if fit:
                enc = LabelEncoder()
                df[f"{col}_encoded"] = enc.fit_transform(df[col].astype(str))
                self.encoders[col] = enc
            else:
                enc = self.encoders.get(col)
                if enc is None:
                    raise RuntimeError(f"Encoder não ajustado para {col}")
                # Trata categorias não vistas
                known = set(enc.classes_)
                df[col] = df[col].astype(str).apply(
                    lambda x: x if x in known else enc.classes_[0]
                )
                df[f"{col}_encoded"] = enc.transform(df[col])
        return df

    def fit_transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Ajusta e transforma o DataFrame.

        Args:
            df: DataFrame com as transações brutas.

        Returns:
            Tupla com (DataFrame com features, matriz numpy escalonada).
        """
        logger.info("iniciando_preprocessamento", total=len(df))

        df = self._criar_features_temporais(df)
        df = self._criar_features_valor(df)
        df = self._criar_features_cliente(df)
        df = self._encodar_categoricas(df, fit=True)

        self.feature_columns = [
            "valor_log",
            "hora",
            "dia_semana",
            "is_madrugada",
            "is_fim_semana",
            "frequencia_cliente",
            "valor_medio_cliente",
            "valor_std_cliente",
            "desvio_valor_cliente",
            "tipo_transacao_encoded",
            "local_encoded",
            "dispositivo_encoded",
        ]

        X = df[self.feature_columns].fillna(0).values
        X_scaled = self.scaler.fit_transform(X)
        self._fitted = True

        logger.info(
            "preprocessamento_concluido",
            features=len(self.feature_columns),
            shape=X_scaled.shape,
        )
        return df, X_scaled

    def transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Transforma novo DataFrame usando preprocessador ajustado.

        Args:
            df: DataFrame com transações novas.

        Returns:
            Tupla com (DataFrame com features, matriz numpy escalonada).
        """
        if not self._fitted:
            raise RuntimeError("Preprocessor não foi ajustado. Use fit_transform primeiro.")

        df = self._criar_features_temporais(df)
        df = self._criar_features_valor(df)
        df = self._criar_features_cliente(df)
        df = self._encodar_categoricas(df, fit=False)

        X = df[self.feature_columns].fillna(0).values
        X_scaled = self.scaler.transform(X)
        return df, X_scaled
