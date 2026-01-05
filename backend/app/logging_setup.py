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
        """Add custom fields to the log record.

        Adds timestamp, level, event name, and exception info to each log entry.

        Args:
            log_record: The dictionary that will be serialized to JSON.
            record: The original logging.LogRecord object.
            message_dict: Dictionary of message-specific fields.

        Returns:
            None
        """
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
    """Configure JSON logging to file and console.

    Sets up a file handler with JSON formatting and a console handler with
    human-readable formatting. Creates the log directory if it doesn't exist.

    Returns:
        None

    Raises:
        OSError: If the log directory cannot be created.
    """
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
    """Get a logger with the given name.

    Args:
        name: The name for the logger, typically the module's __name__.

    Returns:
        A logging.Logger instance configured with the application's settings.
    """
    return logging.getLogger(name)
