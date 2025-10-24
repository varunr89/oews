import json
import logging
from pathlib import Path
from src.utils.logger import setup_workflow_logger, JsonFormatter


def test_logger_creates_log_directory():
    """Test that logger creates logs directory."""
    logger = setup_workflow_logger()

    assert Path("logs").exists()
    assert logger is not None


def test_logger_writes_json_format():
    """Test that logger writes JSON formatted logs."""
    logger = setup_workflow_logger()

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add a handler that writes to a test file
    from logging.handlers import RotatingFileHandler
    test_handler = RotatingFileHandler("logs/test.log", maxBytes=1000, backupCount=1)
    test_handler.setFormatter(JsonFormatter())
    logger.addHandler(test_handler)

    # Write a test log
    logger.debug("test_event", extra={"data": {"key": "value"}})

    # Read back and verify JSON format
    with open("logs/test.log") as f:
        log_line = f.readline()
        log_data = json.loads(log_line)

    assert log_data["level"] == "DEBUG"
    assert log_data["event"] == "test_event"
    assert log_data["data"]["key"] == "value"

    # Cleanup
    Path("logs/test.log").unlink(missing_ok=True)


def test_json_formatter_includes_timestamp():
    """Test that JSON formatter includes timestamp."""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.DEBUG,
        pathname="",
        lineno=0,
        msg="test_message",
        args=(),
        exc_info=None
    )

    formatted = formatter.format(record)
    log_data = json.loads(formatted)

    assert "timestamp" in log_data
    assert "level" in log_data
    assert "component" in log_data
