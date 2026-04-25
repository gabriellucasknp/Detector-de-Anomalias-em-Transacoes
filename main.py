"""
Entry point principal do Detector de Anomalias.

Executa o pipeline completo:
1. Carrega transações (MySQL ou CSV de fallback)
2. Pré-processamento + feature engineering (Pandas)
3. Detecção com Isolation Forest + DBSCAN/Z-Score
4. Avaliação de métricas (se houver labels verdadeiros)
5. Geração de visualizações
6. Persistência dos resultados no MySQL

Uso:
    python main.py
    python main.py --source csv
    python main.py --no-spark
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.anomaly_detector import detectar_anomalias_combinado, montar_df_anomalias
from src.data_loader import (
    carregar_transacoes_csv,
    carregar_transacoes_mysql,
    salvar_anomalias_mysql,
)
from src.evaluator import avaliar, imprimir_relatorio
from src.logger import logger
from src.preprocessor import TransactionPreprocessor
from src.visualizations import gerar_todos_graficos


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline de detecção de anomalias")
    parser.add_argument(
        "--source", choices=["mysql", "csv", "auto"], default="auto",
        help="Fonte de dados (padrão: auto - tenta MySQL, cai pra CSV).",
    )
    parser.add_argument(
        "--csv-path", default="data/raw/transacoes.csv",
        help="Caminho do CSV (quando source=csv).",
    )
    parser.add_argument(
        "--use-spark", action="store_true",
        help="Usa PySpark para ler e processar (requer MySQL + Java).",
    )
    parser.add_argument(
        "--save-mysql", action="store_true",
        help="Salva os resultados no MySQL.",
    )
    parser.add_argument(
        "--contamination", type=float, default=0.03,
        help="Taxa esperada de anomalias (default 0.03).",
    )
    return parser.parse_args()


def carregar_dados(args: argparse.Namespace) -> pd.DataFrame:
    """Carrega transações da fonte escolhida."""
    if args.use_spark:
        logger.info("usando_pipeline_pyspark")
        from src.pyspark_pipeline import executar_pipeline_spark
        df = executar_pipeline_spark()
        # Renomeia colunas se necessário (Spark preserva nomes)
        return df

    if args.source == "mysql":
        return carregar_transacoes_mysql()

    if args.source == "csv":
        return carregar_transacoes_csv(args.csv_path)

    # auto: tenta MySQL; se falhar, usa CSV
    try:
        df = carregar_transacoes_mysql()
        if len(df) == 0:
            raise RuntimeError("Tabela vazia.")
        return df
    except Exception as e:
        logger.warning("mysql_indisponivel_usando_csv", erro=str(e))
        if not Path(args.csv_path).exists():
            logger.error("csv_tambem_nao_encontrado", path=args.csv_path)
            logger.info("dica: execute 'python src/populate_data.py' primeiro")
            sys.exit(1)
        return carregar_transacoes_csv(args.csv_path)


def main() -> None:
    args = parse_args()
    logger.info("pipeline_iniciando", **vars(args))

    # 1. Carregar dados
    df = carregar_dados(args)
    logger.info("dados_carregados", total=len(df), colunas=list(df.columns))

    if len(df) == 0:
        logger.error("dataset_vazio")
        return

    # 2. Pré-processamento
    preprocessor = TransactionPreprocessor()
    df_features, X = preprocessor.fit_transform(df)

    # 3. Detecção combinada
    r_iforest, r_dbscan = detectar_anomalias_combinado(
        X, contamination=args.contamination
    )

    # 4. Avaliação (se houver labels verdadeiros)
    if "is_anomaly_true" in df_features.columns:
        y_true = df_features["is_anomaly_true"].values
        print(imprimir_relatorio(y_true, r_iforest.labels, "Isolation Forest"))
        print(imprimir_relatorio(y_true, r_dbscan.labels, "DBSCAN + Z-Score"))
        metrics_if = avaliar(y_true, r_iforest.labels, r_iforest.scores, "isolation_forest")
        metrics_db = avaliar(y_true, r_dbscan.labels, r_dbscan.scores, "dbscan_zscore")
        print(f"\n[METRICAS] Isolation Forest: F1={metrics_if.f1:.3f} | AUC={metrics_if.auc_roc:.3f}")
        print(f"[METRICAS] DBSCAN+ZScore:   F1={metrics_db.f1:.3f} | AUC={metrics_db.auc_roc:.3f}\n")

    # 5. Monta DataFrames para persistência e plot
    df_anom_if = montar_df_anomalias(df_features, r_iforest)
    df_anom_db = montar_df_anomalias(df_features, r_dbscan)

    # 6. Visualizações (usa labels do Isolation Forest)
    df_viz = df_features.copy()
    df_viz["is_anomaly"] = r_iforest.labels
    try:
        paths = gerar_todos_graficos(df_viz)
        logger.info("graficos_gerados", **paths)
    except Exception as e:
        logger.error("erro_graficos", erro=str(e))

    # 7. Persistência (opcional)
    if args.save_mysql:
        try:
            salvar_anomalias_mysql(df_anom_if)
            salvar_anomalias_mysql(df_anom_db)
            logger.info("resultados_salvos_mysql")
        except Exception as e:
            logger.error("erro_ao_salvar_mysql", erro=str(e))

    # 8. Exporta resultados em CSV
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    df_anom_if.to_csv("data/processed/anomalias_isolation_forest.csv", index=False)
    df_anom_db.to_csv("data/processed/anomalias_dbscan.csv", index=False)
    logger.info("resultados_exportados_csv")

    print("\n[OK] Pipeline concluido com sucesso!")
    print(f"   - Total de transacoes: {len(df)}")
    print(f"   - Anomalias (Isolation Forest): {int(r_iforest.labels.sum())}")
    print(f"   - Anomalias (DBSCAN+ZScore):    {int(r_dbscan.labels.sum())}")
    print(f"   - Dashboard: data/processed/05_dashboard.html\n")


if __name__ == "__main__":
    main()
