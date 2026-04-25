"""Fixtures compartilhadas para os testes."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def df_transacoes_sample() -> pd.DataFrame:
    """DataFrame pequeno com transações simuladas (normal + anomalias)."""
    np.random.seed(42)
    n_normal = 180
    n_anom = 20

    base = datetime(2024, 1, 1)
    dados = []

    # Normais
    for i in range(n_normal):
        dados.append({
            "id": i + 1,
            "cliente_id": np.random.randint(1, 30),
            "valor": float(np.random.lognormal(4.5, 1.0)),
            "data_transacao": base + timedelta(hours=i),
            "tipo_transacao": np.random.choice(["compra", "transferencia", "saque"]),
            "local": np.random.choice(["São Paulo", "Rio de Janeiro", "Curitiba"]),
            "dispositivo": np.random.choice(["mobile", "web"]),
            "ip_address": "192.168.0.1",
            "is_anomaly_true": 0,
        })

    # Anomalias
    for i in range(n_anom):
        dados.append({
            "id": n_normal + i + 1,
            "cliente_id": np.random.randint(1, 30),
            "valor": float(np.random.uniform(5000, 50000)),  # valores altos
            "data_transacao": base + timedelta(hours=n_normal + i),
            "tipo_transacao": "saque",
            "local": "País Estrangeiro",
            "dispositivo": "atm",
            "ip_address": "10.0.0.1",
            "is_anomaly_true": 1,
        })

    return pd.DataFrame(dados)
