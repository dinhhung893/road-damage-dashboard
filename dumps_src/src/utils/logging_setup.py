"""Structured logging framework for the application.

Provides rotating file logging + console output.
Log file: outputs/app.log (5MB max, 3 backups)
Console: INFO level
File: DEBUG level
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_LOG_DIR = Path("outputs")
_LOG_FILE = _LOG_DIR / "app.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5MB
_BACKUP_COUNT = 3

_initialized = False


def setup_logging(level: int = logging.DEBUG) -> None:
    """Initialize root logger with console + rotating file handlers."""
    global _initialized
    if _initialized:
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Console handler — INFO
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(console)

    # File handler — DEBUG, rotating
    file_handler = RotatingFileHandler(
        str(_LOG_FILE),
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(file_handler)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. Auto-initializes logging if not done yet."""
    if not _initialized:
        setup_logging()
    return logging.getLogger(name)
