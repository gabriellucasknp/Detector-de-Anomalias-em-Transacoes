"""
Módulo de configuração e conexão com o banco de dados MySQL.

Fornece funções para criar engines SQLAlchemy e conexões nativas mysql-connector,
com suporte a variáveis de ambiente e configuração via YAML.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

# Imports dos drivers MySQL/SQLAlchemy são feitos de forma preguiçosa (lazy)
# dentro das funções para permitir uso do módulo em modo CSV-only sem
# exigir instalação dessas dependências opcionais.
if TYPE_CHECKING:
    from mysql.connector.connection import MySQLConnection
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session


@dataclass
class DatabaseConfig:
    """Configuração de conexão com o MySQL."""

    host: str
    port: int
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Cria configuração a partir de variáveis de ambiente."""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "rootpass"),
            database=os.getenv("DB_NAME", "anomaly_db"),
        )

    @property
    def sqlalchemy_url(self) -> str:
        """Retorna URL de conexão SQLAlchemy (PyMySQL)."""
        return (
            f"mysql+pymysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}?charset=utf8mb4"
        )

    @property
    def jdbc_url(self) -> str:
        """Retorna URL JDBC (usado pelo PySpark)."""
        return f"jdbc:mysql://{self.host}:{self.port}/{self.database}"


# Singleton de engine SQLAlchemy
_engine: Optional[Any] = None


def get_engine(config: Optional[DatabaseConfig] = None) -> Any:
    """
    Retorna (e cacheia) uma engine SQLAlchemy.

    Args:
        config: Configuração opcional. Se None, carrega do ambiente.

    Returns:
        Engine do SQLAlchemy configurada com pool de conexões.
    """
    # Import preguiçoso: só exige SQLAlchemy se alguém chamar essa função
    from sqlalchemy import create_engine

    global _engine
    if _engine is None:
        cfg = config or DatabaseConfig.from_env()
        _engine = create_engine(
            cfg.sqlalchemy_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def get_session() -> Any:
    """Retorna uma nova sessão SQLAlchemy."""
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return SessionLocal()


def get_connection(config: Optional[DatabaseConfig] = None) -> Any:
    """
    Retorna uma conexão nativa mysql-connector-python.

    Útil para operações em lote (bulk inserts) onde SQLAlchemy é mais lento.

    Args:
        config: Configuração opcional.

    Returns:
        Conexão MySQL.
    """
    # Import preguiçoso: mysql-connector só é exigido se usado
    import mysql.connector

    cfg = config or DatabaseConfig.from_env()
    return mysql.connector.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
        autocommit=False,
    )


def test_connection() -> bool:
    """
    Testa a conexão com o banco de dados.

    Returns:
        True se a conexão foi bem-sucedida, False caso contrário.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao conectar: {e}")
        return False
