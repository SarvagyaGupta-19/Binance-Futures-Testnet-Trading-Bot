"""
bot.logging_config
~~~~~~~~~~~~~~~~~~
Centralised logging configuration for the trading bot.

Two handlers are attached to the root 'trading_bot' logger:
  - RotatingFileHandler: captures DEBUG and above as structured JSON lines.
  - StreamHandler: surfaces WARNING and above as plain text on stderr.

Use get_logger(__name__) in every module to obtain a named child logger.
"""

import json
import logging
import logging.handlers
import os
from datetime import datetime, timezone

# Log file sits at the trading_bot/ root, one level above this module.
LOG_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "trading_bot.log"))

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file before rotation
_BACKUP_COUNT = 3              # Keep up to 3 rotated files

# Fields that are standard LogRecord attributes — never forwarded as extras.
_STDLIB_FIELDS = frozenset(logging.LogRecord(
    "", 0, "", 0, "", (), None
).__dict__.keys()) | {"message", "asctime"}


class _JsonFormatter(logging.Formatter):
    """Formats each log record as a single-line JSON object.

    Core fields (timestamp, level, logger, message) are always present.
    Any extra context passed via logger.xxx(..., extra={...}) is appended
    as additional top-level keys.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Append exception traceback when present.
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Append only caller-supplied extra fields; skip all stdlib internals.
        for key, value in record.__dict__.items():
            if key not in _STDLIB_FIELDS and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Attach handlers to the root 'trading_bot' logger.

    Idempotent — safe to call multiple times; handlers are only added once.
    """
    root = logging.getLogger("trading_bot")
    if root.handlers:
        return

    root.setLevel(logging.DEBUG)

    # File handler — full DEBUG trace, JSON structured.
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_JsonFormatter())
    root.addHandler(file_handler)

    # Stream handler — WARNING+ only; keeps the terminal uncluttered.
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARNING)
    stream_handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
    root.addHandler(stream_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named child logger under the 'trading_bot' hierarchy.

    Args:
        name: Typically the calling module's __name__.

    Returns:
        A logging.Logger instance.

    Example:
        logger = get_logger(__name__)
        logger.info("Order placed", extra={"orderId": 12345})
    """
    configure_logging()
    return logging.getLogger(f"trading_bot.{name}")
