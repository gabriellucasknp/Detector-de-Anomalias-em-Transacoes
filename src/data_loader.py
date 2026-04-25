"""
Módulo de carregamento de dados.

Responsável por ler transações do MySQL ou de arquivos CSV,
retornando DataFrames Pandas prontos para uso no pipeline.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from config.database import get_engine
from src.logger import logger


def carregar_transacoes_mysql(
    limit: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> pd.DataFrame:
    """
    Carrega transações do MySQL em um DataFrame Pandas.

    Args:
        limit: Limite de linhas a carregar.
        date_from: Data inicial (formato 'YYYY-MM-DD').
        date_to: Data final (formato 'YYYY-MM-DD').

    Returns:
        DataFrame com as transações.
    """
    engine = get_engine()
    query = "SELECT * FROM transacoes WHERE 1=1"
    params: dict = {}

    if date_from:
        query += " AND data_transacao >= :date_from"
        params["date_from"] = date_from
    if date_to:
        query += " AND data_transacao <= :date_to"
        params["date_to"] = date_to

    query += " ORDER BY data_transacao DESC"

    if limit:
        query += f" LIMIT {int(limit)}"

    logger.info("carregando_transacoes_mysql", query=query)
    df = pd.read_sql(query, engine, params=params)
    logger.info("transacoes_carregadas", total=len(df))
    return df


def carregar_transacoes_csv(path: str = "data/raw/transacoes.csv") -> pd.DataFrame:
    """
    Carrega transações de um arquivo CSV.

    Args:
        path: Caminho do arquivo CSV.

    Returns:
        DataFrame com as transações.
    """
    caminho = Path(path)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    logger.info("carregando_csv", path=path)
    df = pd.read_csv(path, parse_dates=["data_transacao"])
    logger.info("csv_carregado", total=len(df))
    return df


def salvar_anomalias_mysql(df_anomalias: pd.DataFrame) -> int:
    """
    Salva resultados de anomalias detectadas no MySQL.

    Args:
        df_anomalias: DataFrame com colunas:
            [transacao_id, cliente_id, score_anomalia,
             metodo_deteccao, is_anomaly, detalhes]

    Returns:
        Número de linhas inseridas.
    """
    engine = get_engine()

    colunas_esperadas = [
        "transacao_id", "cliente_id", "score_anomalia",
        "metodo_deteccao", "is_anomaly",
    ]
    for col in colunas_esperadas:
        if col not in df_anomalias.columns:
            raise ValueError(f"Coluna obrigatória ausente: {col}")

    df_to_save = df_anomalias[colunas_esperadas].copy()
    if "detalhes" in df_anomalias.columns:
        df_to_save["detalhes"] = df_anomalias["detalhes"]

    # Limpa anomalias anteriores do mesmo método
    metodos = df_to_save["metodo_deteccao"].unique().tolist()
    with engine.begin() as conn:
        for metodo in metodos:
            conn.exec_driver_sql(
                "DELETE FROM anomalias WHERE metodo_deteccao = %s", (metodo,)
            )

    df_to_save.to_sql("anomalias", engine, if_exists="append", index=False)
    logger.info("anomalias_salvas", total=len(df_to_save), metodos=metodos)
    return len(df_to_save)
