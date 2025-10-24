"""Structured logging for workflow observability."""

import logging
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string with timestamp, level, component, event, and optional data
        """
        log_data = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "component": record.name,
            "event": record.getMessage(),
        }

        # Include extra data if provided
        if hasattr(record, 'data'):
            log_data['data'] = record.data

        return json.dumps(log_data)


def setup_workflow_logger(name: str = "oews.workflow") -> logging.Logger:
    """
    Set up structured logger for workflow debugging.

    Creates logs/ directory if it doesn't exist.
    Configures rotating file handler (10MB files, keep 5).

    Args:
        name: Logger name (default: oews.workflow)

    Returns:
        Configured logger instance
    """
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    # Create rotating file handler
    handler = RotatingFileHandler(
        "logs/workflow_debug.log",
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )

    # Set JSON formatter
    handler.setFormatter(JsonFormatter())

    # Add handler to logger
    logger.addHandler(handler)

    return logger
