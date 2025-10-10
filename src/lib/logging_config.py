"""
Comprehensive Logging Configuration

Structured JSON logging with multiple handlers and formatters.
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data

        return json.dumps(log_data)


class ContextFilter(logging.Filter):
    """Add contextual information to log records"""

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.context = context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add context to log record

        Args:
            record: Log record to filter

        Returns:
            Always True (we don't actually filter)
        """
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


def setup_logging(
    log_dir: Path = Path('logs'),
    log_level: str = 'INFO',
    enable_json: bool = False,
    enable_file: bool = True,
    enable_console: bool = True,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Configure comprehensive logging

    Args:
        log_dir: Directory for log files
        log_level: Logging level
        enable_json: Use JSON formatting
        enable_file: Enable file logging
        enable_console: Enable console logging
        context: Contextual information to add to all logs
    """
    # Create log directory
    log_dir.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatters
    if enable_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Add context filter if provided
    if context:
        context_filter = ContextFilter(context)
        root_logger.addFilter(context_filter)

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if enable_file:
        log_file = log_dir / f"oews_migration_{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Error file handler (errors only)
    if enable_file:
        error_log_file = log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"

        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)

    logging.info(f"Logging configured: level={log_level}, json={enable_json}")


def get_logger(name: str, extra_context: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Get a logger with optional extra context

    Args:
        name: Logger name
        extra_context: Extra contextual information

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    if extra_context:
        # Add context filter to this logger
        context_filter = ContextFilter(extra_context)
        logger.addFilter(context_filter)

    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter for adding context"""

    def process(self, msg, kwargs):
        """
        Process log message with extra context

        Args:
            msg: Log message
            kwargs: Keyword arguments

        Returns:
            Processed message and kwargs
        """
        if 'extra_data' in self.extra:
            if 'extra' not in kwargs:
                kwargs['extra'] = {}
            kwargs['extra']['extra_data'] = self.extra['extra_data']

        return msg, kwargs
