"""Конфигурация логирования, общая для всех точек входа."""

import logging

from app.core.config import settings


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=LOG_FORMAT,
        force=True,
    )
