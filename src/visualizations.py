"""
Módulo de visualizações para o Detector de Anomalias.

Gera os gráficos obrigatórios:
1. Distribuição de valores (normal vs anomalias)
2. Timeseries de transações
3. Heatmap de correlações
4. Scatter plot 2D das anomalias
5. Dashboard interativo em Plotly
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # backend não-interativo (servidor/docker)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from plotly.subplots import make_subplots

from src.logger import logger

sns.set_theme(style="whitegrid")


def _garantir_dir(path: str) -> Path:
    """Garante que o diretório pai exista."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def plot_distribuicao_valores(
    df: pd.DataFrame,
    col_valor: str = "valor",
    col_anomaly: str = "is_anomaly",
    output_path: str = "data/processed/01_distribuicao_valores.png",
) -> str:
    """Histograma + boxplot de valores, separando normais vs anomalias."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    normais = df[df[col_anomaly] == 0][col_valor]
    anomalias = df[df[col_anomaly] == 1][col_valor]

    # Histograma (escala log)
    axes[0].hist(np.log1p(normais), bins=50, alpha=0.6, label="Normal", color="steelblue")
    axes[0].hist(np.log1p(anomalias), bins=50, alpha=0.6, label="Anomalia", color="crimson")
    axes[0].set_xlabel("log(1 + valor)")
    axes[0].set_ylabel("Frequência")
    axes[0].set_title("Distribuição de Valores (escala log)")
    axes[0].legend()

    # Boxplot
    df_plot = df.copy()
    df_plot["tipo"] = df_plot[col_anomaly].map({0: "Normal", 1: "Anomalia"})
    sns.boxplot(data=df_plot, x="tipo", y=col_valor, ax=axes[1], palette=["steelblue", "crimson"])
    axes[1].set_yscale("log")
    axes[1].set_title("Boxplot de Valores por Categoria")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("Valor (log)")

    plt.tight_layout()
    out = _garantir_dir(output_path)
    plt.savefig(out, dpi=100, bbox_inches="tight")
    plt.close(fig)
    logger.info("plot_salvo", arquivo=str(out))
    return str(out)


def plot_timeseries(
    df: pd.DataFrame,
    col_data: str = "data_transacao",
    col_anomaly: str = "is_anomaly",
    output_path: str = "data/processed/02_timeseries.png",
) -> str:
    """Série temporal de transações por dia, destacando anomalias."""
    df = df.copy()
    df[col_data] = pd.to_datetime(df[col_data])
    df["dia"] = df[col_data].dt.date

    agg = (
        df.groupby(["dia", col_anomaly])
        .size()
        .unstack(fill_value=0)
        .rename(columns={0: "normais", 1: "anomalias"})
    )

    fig, ax = plt.subplots(figsize=(14, 5))
    if "normais" in agg.columns:
        ax.plot(agg.index, agg["normais"], label="Normais", color="steelblue", linewidth=2)
    if "anomalias" in agg.columns:
        ax.plot(agg.index, agg["anomalias"], label="Anomalias", color="crimson", linewidth=2)
        ax.fill_between(agg.index, 0, agg["anomalias"], alpha=0.3, color="crimson")

    ax.set_xlabel("Data")
    ax.set_ylabel("Nº de transações")
    ax.set_title("Série temporal de transações")
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()

    out = _garantir_dir(output_path)
    plt.savefig(out, dpi=100, bbox_inches="tight")
    plt.close(fig)
    logger.info("plot_salvo", arquivo=str(out))
    return str(out)


def plot_heatmap_correlacoes(
    df: pd.DataFrame,
    output_path: str = "data/processed/03_heatmap_correlacoes.png",
) -> str:
    """Heatmap de correlação entre features numéricas."""
    numeric = df.select_dtypes(include=[np.number])
    # Remove colunas constantes
    numeric = numeric.loc[:, numeric.nunique() > 1]

    corr = numeric.corr()

    fig, ax = plt.subplots(figsize=(12, 9))
    sns.heatmap(
        corr,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
        ax=ax,
        cbar_kws={"shrink": 0.8},
    )
    ax.set_title("Heatmap de Correlações entre Features")
    plt.tight_layout()

    out = _garantir_dir(output_path)
    plt.savefig(out, dpi=100, bbox_inches="tight")
    plt.close(fig)
    logger.info("plot_salvo", arquivo=str(out))
    return str(out)


def plot_scatter_2d(
    df: pd.DataFrame,
    col_x: str = "valor_log",
    col_y: str = "desvio_valor_cliente",
    col_anomaly: str = "is_anomaly",
    output_path: str = "data/processed/04_scatter_anomalias.png",
) -> str:
    """Scatter 2D mostrando anomalias vs normais em duas features."""
    fig, ax = plt.subplots(figsize=(10, 7))

    normais = df[df[col_anomaly] == 0]
    anomalias = df[df[col_anomaly] == 1]

    ax.scatter(normais[col_x], normais[col_y], alpha=0.3, s=15,
               label="Normal", color="steelblue")
    ax.scatter(anomalias[col_x], anomalias[col_y], alpha=0.8, s=40,
               label="Anomalia", color="crimson", edgecolor="black", linewidth=0.5)

    ax.set_xlabel(col_x)
    ax.set_ylabel(col_y)
    ax.set_title(f"Scatter 2D: {col_x} vs {col_y}")
    ax.legend()
    plt.tight_layout()

    out = _garantir_dir(output_path)
    plt.savefig(out, dpi=100, bbox_inches="tight")
    plt.close(fig)
    logger.info("plot_salvo", arquivo=str(out))
    return str(out)


def dashboard_plotly(
    df: pd.DataFrame,
    output_path: str = "data/processed/05_dashboard.html",
) -> str:
    """
    Cria dashboard interativo em Plotly com múltiplas visualizações.

    Args:
        df: DataFrame com colunas: valor, data_transacao, tipo_transacao,
            local, is_anomaly.
        output_path: Caminho do HTML de saída.

    Returns:
        Caminho do arquivo gerado.
    """
    df = df.copy()
    df["data_transacao"] = pd.to_datetime(df["data_transacao"])
    df["tipo"] = df["is_anomaly"].map({0: "Normal", 1: "Anomalia"}).fillna("Normal")

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Distribuição de Valores (log)",
            "Transações por Tipo",
            "Anomalias ao Longo do Tempo",
            "Top 10 Locais com Anomalias",
        ),
        specs=[
            [{"type": "histogram"}, {"type": "bar"}],
            [{"type": "scatter"}, {"type": "bar"}],
        ],
    )

    # 1. Histograma de valores
    for label, color in [("Normal", "steelblue"), ("Anomalia", "crimson")]:
        sub = df[df["tipo"] == label]
        fig.add_trace(
            go.Histogram(
                x=np.log1p(sub["valor"]),
                name=label,
                marker_color=color,
                opacity=0.6,
                nbinsx=50,
            ),
            row=1, col=1,
        )

    # 2. Barras por tipo de transação
    tipo_agg = df.groupby(["tipo_transacao", "tipo"]).size().reset_index(name="count")
    for label, color in [("Normal", "steelblue"), ("Anomalia", "crimson")]:
        sub = tipo_agg[tipo_agg["tipo"] == label]
        fig.add_trace(
            go.Bar(x=sub["tipo_transacao"], y=sub["count"],
                   name=label, marker_color=color, showlegend=False),
            row=1, col=2,
        )

    # 3. Timeseries
    df["dia"] = df["data_transacao"].dt.date
    ts = df.groupby(["dia", "tipo"]).size().reset_index(name="count")
    for label, color in [("Normal", "steelblue"), ("Anomalia", "crimson")]:
        sub = ts[ts["tipo"] == label]
        fig.add_trace(
            go.Scatter(x=sub["dia"], y=sub["count"], mode="lines+markers",
                       name=label, line=dict(color=color), showlegend=False),
            row=2, col=1,
        )

    # 4. Top 10 locais com anomalias
    top_locais = (
        df[df["is_anomaly"] == 1]["local"].value_counts().head(10).reset_index()
    )
    top_locais.columns = ["local", "count"]
    fig.add_trace(
        go.Bar(x=top_locais["local"], y=top_locais["count"],
               marker_color="crimson", showlegend=False),
        row=2, col=2,
    )

    fig.update_layout(
        title_text="Dashboard - Detector de Anomalias em Transações",
        height=800,
        barmode="overlay",
        template="plotly_white",
    )

    out = _garantir_dir(output_path)
    fig.write_html(str(out))
    logger.info("dashboard_salvo", arquivo=str(out))
    return str(out)


def gerar_todos_graficos(df: pd.DataFrame, output_dir: str = "data/processed") -> dict:
    """
    Gera todos os gráficos obrigatórios de uma vez.

    Args:
        df: DataFrame com features e coluna is_anomaly.
        output_dir: Diretório de saída.

    Returns:
        Dicionário com caminhos dos arquivos gerados.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    paths = {
        "distribuicao": plot_distribuicao_valores(
            df, output_path=f"{output_dir}/01_distribuicao_valores.png"
        ),
        "timeseries": plot_timeseries(
            df, output_path=f"{output_dir}/02_timeseries.png"
        ),
        "heatmap": plot_heatmap_correlacoes(
            df, output_path=f"{output_dir}/03_heatmap_correlacoes.png"
        ),
        "scatter": plot_scatter_2d(
            df, output_path=f"{output_dir}/04_scatter_anomalias.png"
        ),
        "dashboard": dashboard_plotly(
            df, output_path=f"{output_dir}/05_dashboard.html"
        ),
    }
    return paths
