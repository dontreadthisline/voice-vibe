from __future__ import annotations
from collections.abc import Callable
from datetime import UTC, datetime
import logging
from logging.handlers import RotatingFileHandler
import os

from pathlib import Path


class GlobalPath:
    def __init__(self, resolver: Callable[[], Path]) -> None:
        self._resolver = resolver

    @property
    def path(self) -> Path:
        return self._resolver()


_DEFAULT_VIBE_HOME = Path.home() / ".vibe"


def _get_vibe_home() -> Path:
    if vibe_home := os.getenv("VIBE_HOME"):
        return Path(vibe_home).expanduser().resolve()
    return _DEFAULT_VIBE_HOME


VIBE_HOME = GlobalPath(_get_vibe_home)
LOG_DIR = GlobalPath(lambda: VIBE_HOME.path / "logs")
LOG_FILE = GlobalPath(lambda: VIBE_HOME.path / "logs" / "vibe.log")

LOG_DIR.path.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("vibe")


class StructuredLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        ppid = os.getppid()
        pid = os.getpid()
        level = record.levelname
        message = record.getMessage().replace("\\", "\\\\").replace("\n", "\\n")

        line = f"{timestamp} {ppid} {pid} {level} {message}"

        if record.exc_info:
            exc_text = self.formatException(record.exc_info).replace("\n", "\\n")
            line = f"{line} {exc_text}"

        return line


def apply_logging_config(target_logger: logging.Logger) -> None:
    LOG_DIR.path.mkdir(parents=True, exist_ok=True)

    max_bytes = int(os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024))

    if os.environ.get("DEBUG_MODE") == "true":
        log_level_str = "DEBUG"
    else:
        log_level_str = os.environ.get("LOG_LEVEL", "WARNING").upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level_str not in valid_levels:
            log_level_str = "WARNING"

    handler = RotatingFileHandler(
        LOG_FILE.path, maxBytes=max_bytes, backupCount=0, encoding="utf-8"
    )
    handler.setFormatter(StructuredLogFormatter())
    log_level = getattr(logging, log_level_str, logging.WARNING)
    handler.setLevel(log_level)

    # Make sure the logger is not gating logs
    target_logger.setLevel(logging.DEBUG)

    target_logger.addHandler(handler)


apply_logging_config(logger)
