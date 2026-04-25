"""
Pipeline PySpark para processamento distribuído de transações.

Embora o scikit-learn seja usado no treinamento final do Isolation Forest
(pois PySpark MLlib não tem IForest nativo), o Spark é usado para:
- Ler grandes volumes via JDBC do MySQL
- Calcular features agregadas em escala (window functions, groupBy)
- Aplicar o modelo treinado em predição paralela (broadcast)
- Persistir resultados de volta no MySQL
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd

from config.database import DatabaseConfig
from src.logger import logger

try:
    from pyspark.sql import DataFrame as SparkDataFrame
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    PYSPARK_AVAILABLE = True
except ImportError:  # pragma: no cover
    PYSPARK_AVAILABLE = False
    SparkSession = None  # type: ignore


def criar_spark_session(app_name: str = "AnomalyDetector") -> "SparkSession":
    """
    Cria e configura uma SparkSession.

    Args:
        app_name: Nome da aplicação Spark.

    Returns:
        SparkSession configurada.
    """
    if not PYSPARK_AVAILABLE:
        raise ImportError("PySpark não está instalado.")

    master = os.getenv("SPARK_MASTER", "local[*]")

    builder = (
        SparkSession.builder
        .appName(app_name)
        .master(master)
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        # Driver MySQL JDBC (baixado automaticamente via Maven)
        .config("spark.jars.packages", "com.mysql:mysql-connector-j:8.2.0")
    )

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    logger.info("spark_session_criada", master=master, app=app_name)
    return spark


def ler_transacoes_jdbc(
    spark: "SparkSession",
    config: Optional[DatabaseConfig] = None,
) -> "SparkDataFrame":
    """
    Lê a tabela `transacoes` do MySQL via JDBC.

    Args:
        spark: SparkSession ativa.
        config: Configuração de banco (opcional).

    Returns:
        Spark DataFrame com as transações.
    """
    cfg = config or DatabaseConfig.from_env()
    df = (
        spark.read
        .format("jdbc")
        .option("url", cfg.jdbc_url)
        .option("dbtable", "transacoes")
        .option("user", cfg.user)
        .option("password", cfg.password)
        .option("driver", "com.mysql.cj.jdbc.Driver")
        .load()
    )
    logger.info("transacoes_lidas_spark", count=df.count())
    return df


def feature_engineering_spark(df: "SparkDataFrame") -> "SparkDataFrame":
    """
    Aplica feature engineering distribuído.

    Features criadas:
    - valor_log
    - hora, dia_semana, is_madrugada, is_fim_semana
    - frequencia_cliente, valor_medio_cliente, valor_std_cliente (via window)
    - desvio_valor_cliente

    Args:
        df: DataFrame Spark com colunas originais de transações.

    Returns:
        DataFrame com features adicionadas.
    """
    logger.info("feature_engineering_spark_iniciando")

    df = df.withColumn("valor", F.col("valor").cast("double"))
    df = df.withColumn("valor_log", F.log1p(F.col("valor")))
    df = df.withColumn("hora", F.hour("data_transacao"))
    df = df.withColumn("dia_semana", (F.dayofweek("data_transacao") - 1))
    df = df.withColumn(
        "is_madrugada",
        ((F.col("hora") >= 0) & (F.col("hora") <= 6)).cast("int"),
    )
    df = df.withColumn(
        "is_fim_semana",
        (F.col("dia_semana") >= 5).cast("int"),
    )

    # Agregações por cliente via window
    w = Window.partitionBy("cliente_id")
    df = (
        df
        .withColumn("frequencia_cliente", F.count("valor").over(w))
        .withColumn("valor_medio_cliente", F.avg("valor").over(w))
        .withColumn("valor_std_cliente", F.coalesce(F.stddev("valor").over(w), F.lit(0.0)))
    )
    df = df.withColumn(
        "desvio_valor_cliente",
        (F.col("valor") - F.col("valor_medio_cliente"))
        / (F.col("valor_std_cliente") + F.lit(1e-6)),
    )

    logger.info("feature_engineering_spark_concluido")
    return df


def spark_para_pandas(df: "SparkDataFrame") -> pd.DataFrame:
    """
    Converte DataFrame Spark para Pandas (coleta no driver).

    Só use quando o dataset cabe na memória do driver!

    Args:
        df: Spark DataFrame.

    Returns:
        Pandas DataFrame.
    """
    logger.info("convertendo_spark_para_pandas")
    pdf = df.toPandas()
    logger.info("conversao_concluida", rows=len(pdf))
    return pdf


def escrever_anomalias_jdbc(
    spark: "SparkSession",
    pdf_anomalias: pd.DataFrame,
    config: Optional[DatabaseConfig] = None,
) -> int:
    """
    Persiste resultados de anomalias no MySQL via Spark JDBC.

    Args:
        spark: SparkSession ativa.
        pdf_anomalias: Pandas DataFrame com as anomalias.
        config: Configuração de banco.

    Returns:
        Número de linhas escritas.
    """
    cfg = config or DatabaseConfig.from_env()

    # Garante tipos corretos
    pdf_anomalias = pdf_anomalias.copy()
    pdf_anomalias["is_anomaly"] = pdf_anomalias["is_anomaly"].astype(int)
    pdf_anomalias["score_anomalia"] = pdf_anomalias["score_anomalia"].astype(float)

    sdf = spark.createDataFrame(pdf_anomalias)

    (
        sdf.write
        .format("jdbc")
        .option("url", cfg.jdbc_url)
        .option("dbtable", "anomalias")
        .option("user", cfg.user)
        .option("password", cfg.password)
        .option("driver", "com.mysql.cj.jdbc.Driver")
        .mode("append")
        .save()
    )

    logger.info("anomalias_escritas_spark", total=len(pdf_anomalias))
    return len(pdf_anomalias)


def executar_pipeline_spark() -> pd.DataFrame:
    """
    Executa o pipeline Spark completo:
    1. Cria SparkSession
    2. Lê transações do MySQL
    3. Aplica feature engineering
    4. Converte para Pandas para modelagem

    Returns:
        DataFrame Pandas com features (pronto para os detectores).
    """
    spark = criar_spark_session()
    try:
        sdf = ler_transacoes_jdbc(spark)
        sdf = feature_engineering_spark(sdf)
        pdf = spark_para_pandas(sdf)
        return pdf
    finally:
        spark.stop()
        logger.info("spark_session_finalizada")
