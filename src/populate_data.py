"""
Gerador de dados sintéticos de transações financeiras.

Gera ~10.000 transações realistas, incluindo 2-5% de anomalias
(valores extremos, frequência alta, locais suspeitos, dispositivos incomuns).
Persiste no MySQL e também exporta CSV para data/raw/.
"""
from __future__ import annotations

import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
from faker import Faker

from config.database import get_connection
from src.logger import logger

# Semente para reprodutibilidade
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
fake = Faker("pt_BR")
Faker.seed(RANDOM_SEED)

# Catálogos
TIPOS_TRANSACAO = ["compra", "transferencia", "saque", "pagamento", "deposito"]
LOCAIS_NORMAIS = [
    "São Paulo", "Rio de Janeiro", "Belo Horizonte", "Brasília",
    "Salvador", "Fortaleza", "Curitiba", "Manaus", "Porto Alegre", "Recife",
]
LOCAIS_SUSPEITOS = ["Desconhecido", "País Estrangeiro", "VPN Location", "TOR Exit Node"]
DISPOSITIVOS = ["mobile", "web", "atm", "pos"]


def _gerar_transacao_normal(cliente_id: int, data_base: datetime) -> dict:
    """Gera uma transação com características normais."""
    return {
        "cliente_id": cliente_id,
        "valor": round(np.random.lognormal(mean=4.5, sigma=1.0), 2),  # mediana ~R$90
        "data_transacao": data_base - timedelta(
            days=random.randint(0, 90),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        ),
        "tipo_transacao": random.choice(TIPOS_TRANSACAO),
        "local": random.choice(LOCAIS_NORMAIS),
        "dispositivo": random.choice(DISPOSITIVOS),
        "ip_address": fake.ipv4(),
    }


def _gerar_transacao_anomala(cliente_id: int, data_base: datetime) -> dict:
    """
    Gera uma transação anômala.

    Tipos de anomalia:
    - valor_extremo: valor muito alto
    - local_suspeito: local fora do padrão
    - horario_incomum: madrugada
    - dispositivo_raro: combinação incomum
    """
    tipo_anomalia = random.choice(
        ["valor_extremo", "local_suspeito", "horario_incomum", "dispositivo_raro"]
    )

    transacao = _gerar_transacao_normal(cliente_id, data_base)

    if tipo_anomalia == "valor_extremo":
        # Valor 50x a 500x maior que a mediana
        transacao["valor"] = round(random.uniform(5000, 100000), 2)
    elif tipo_anomalia == "local_suspeito":
        transacao["local"] = random.choice(LOCAIS_SUSPEITOS)
        transacao["valor"] = round(random.uniform(500, 10000), 2)
    elif tipo_anomalia == "horario_incomum":
        # Transação na madrugada (2h-5h)
        transacao["data_transacao"] = transacao["data_transacao"].replace(
            hour=random.randint(2, 5)
        )
        transacao["valor"] = round(random.uniform(1000, 20000), 2)
    else:  # dispositivo_raro
        transacao["dispositivo"] = "atm"
        transacao["local"] = random.choice(LOCAIS_SUSPEITOS)
        transacao["valor"] = round(random.uniform(2000, 15000), 2)

    return transacao


def gerar_dataset(
    n_transacoes: int = 10_000,
    n_clientes: int = 500,
    anomaly_rate: float = 0.03,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Gera um DataFrame com transações sintéticas.

    Args:
        n_transacoes: Total de transações a gerar.
        n_clientes: Quantidade de clientes distintos.
        anomaly_rate: Proporção de anomalias (0.02 a 0.05 recomendado).

    Returns:
        Tupla com (DataFrame de transações, Series com labels verdadeiros).
    """
    logger.info(
        "gerando_dataset_sintetico",
        n_transacoes=n_transacoes,
        n_clientes=n_clientes,
        anomaly_rate=anomaly_rate,
    )

    n_anomalias = int(n_transacoes * anomaly_rate)
    n_normais = n_transacoes - n_anomalias
    data_base = datetime.now()

    registros: List[dict] = []
    labels: List[int] = []

    # Transações normais
    for _ in range(n_normais):
        cliente_id = random.randint(1, n_clientes)
        registros.append(_gerar_transacao_normal(cliente_id, data_base))
        labels.append(0)

    # Transações anômalas
    for _ in range(n_anomalias):
        cliente_id = random.randint(1, n_clientes)
        registros.append(_gerar_transacao_anomala(cliente_id, data_base))
        labels.append(1)

    df = pd.DataFrame(registros)
    labels_series = pd.Series(labels, name="is_anomaly_true")

    # Embaralha mantendo alinhamento entre df e labels
    idx = np.random.permutation(len(df))
    df = df.iloc[idx].reset_index(drop=True)
    labels_series = labels_series.iloc[idx].reset_index(drop=True)

    logger.info(
        "dataset_gerado",
        total=len(df),
        anomalias=int(labels_series.sum()),
        normais=int((labels_series == 0).sum()),
    )

    return df, labels_series


def salvar_no_mysql(df: pd.DataFrame, batch_size: int = 1000) -> int:
    """
    Persiste o DataFrame no MySQL (tabela `transacoes`).

    Args:
        df: DataFrame com as colunas compatíveis com a tabela.
        batch_size: Tamanho do lote para insert em massa.

    Returns:
        Número de linhas inseridas.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Limpa dados anteriores
    cursor.execute("DELETE FROM anomalias")
    cursor.execute("DELETE FROM transacoes")
    cursor.execute("ALTER TABLE transacoes AUTO_INCREMENT = 1")
    conn.commit()

    insert_sql = """
        INSERT INTO transacoes
            (cliente_id, valor, data_transacao, tipo_transacao, local, dispositivo, ip_address)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    total = 0
    registros = df[
        ["cliente_id", "valor", "data_transacao", "tipo_transacao",
         "local", "dispositivo", "ip_address"]
    ].values.tolist()

    for i in range(0, len(registros), batch_size):
        batch = registros[i:i + batch_size]
        cursor.executemany(insert_sql, batch)
        conn.commit()
        total += len(batch)
        logger.info("batch_inserido", lote=i // batch_size + 1, registros=total)

    cursor.close()
    conn.close()
    return total


def salvar_csv(df: pd.DataFrame, labels: pd.Series, path: str = "data/raw/transacoes.csv") -> None:
    """Salva CSV com transações + labels verdadeiros (para avaliação)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df_out = df.copy()
    df_out["is_anomaly_true"] = labels.values
    df_out.to_csv(path, index=False)
    logger.info("csv_salvo", path=path, registros=len(df_out))


def main() -> None:
    """Entry point: gera dados e persiste no MySQL + CSV."""
    df, labels = gerar_dataset(n_transacoes=10_000, n_clientes=500, anomaly_rate=0.03)

    # Sempre salva CSV (não depende do MySQL estar up)
    salvar_csv(df, labels)

    # Tenta salvar no MySQL
    try:
        total = salvar_no_mysql(df)
        logger.info("populacao_concluida", total_inserido=total)
    except Exception as e:
        logger.error("erro_ao_salvar_mysql", erro=str(e))
        logger.warning("dados_disponiveis_apenas_em_csv")


if __name__ == "__main__":
    main()
