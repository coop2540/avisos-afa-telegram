"""Configuració de logging cap a stdout, sense exposar secrets."""

from __future__ import annotations

import logging
import os
import sys

_LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

_configured = False


def mask_secret(value: str | None, visible: int = 4) -> str:
    """Retorna una versió segura d'un secret per a logs.

    No s'ha d'usar per reconstruir el secret, només per diagnosticar.
    """
    if not value:
        return "<buit>"
    if len(value) <= visible:
        return "*" * len(value)
    return f"{value[:visible]}{'*' * (len(value) - visible)}"


def setup_logging(level: str | None = None) -> None:
    """Configura el logger arrel una sola vegada."""
    global _configured
    if _configured:
        return

    resolved = (level or os.environ.get("LOG_LEVEL") or "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.setLevel(getattr(logging, resolved, logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
