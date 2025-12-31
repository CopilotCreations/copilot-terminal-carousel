"""JSON logging setup for the application."""
import logging
import sys
from pathlib import Path

from pythonjsonlogger import jsonlogger

from app.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with required fields."""

    def add_fields(
        self,
        log_record: dict[str, object],
        record: logging.LogRecord,
        message_dict: dict[str, object],
    ) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)
        # Use ISO format with milliseconds (strftime doesn't support %f)
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        log_record["ts"] = dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{int(record.msecs):03d}Z"
        log_record["level"] = record.levelname
        log_record["event"] = record.name
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)


def setup_logging() -> None:
    """Configure JSON logging to file and console."""
    # Ensure log directory exists
    log_dir = settings.LOG_FILE.parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create formatter
    formatter = CustomJsonFormatter(
        "%(ts)s %(level)s %(event)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S.%fZ",
    )

    # File handler
    file_handler = logging.FileHandler(settings.LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Console handler (for development)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)
