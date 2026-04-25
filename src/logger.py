"""
Módulo de logging estruturado usando structlog.

Fornece logger configurado para uso em toda a aplicação, com saída em JSON
em produção e formato legível em desenvolvimento.
"""
from __future__ import annotations

import logging
import os
import sys

import structlog


def setup_logger(name: str = "anomaly_detector") -> structlog.stdlib.BoundLogger:
    """
    Configura e retorna um logger estruturado.

    Args:
        name: Nome do logger.

    Returns:
        Logger estruturado pronto para uso.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    is_production = os.getenv("APP_ENV", "development") == "production"

    # Configuração do logging padrão do Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO),
    )

    # Processadores compartilhados
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Em produção usa JSON, em dev usa saída colorida
    if is_production:
        processors = shared_processors + [structlog.processors.JSONRenderer()]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger(name)


# Logger padrão da aplicação
logger = setup_logger()
