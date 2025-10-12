"""
CLI Error Handling and Logging Configuration

Centralized error handling and logging setup for CLI operations.
"""

import logging
import sys
import traceback
from pathlib import Path
from typing import Optional
import click

from src.cli.config import config


def setup_logging(log_file: Optional[Path] = None, log_level: str = 'INFO'):
    """
    Configure logging for CLI application

    Args:
        log_file: Path to log file (optional, will use console if not provided)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (simple format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # File handler (detailed format) if log_file specified
    if log_file:
        # Create log directory if it doesn't exist
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always capture debug in file
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

        logging.info(f"Logging to file: {log_file}")


def handle_exception(exc_type, exc_value, exc_traceback):
    """
    Global exception handler

    Args:
        exc_type: Exception type
        exc_value: Exception value
        exc_traceback: Exception traceback
    """
    # Don't catch keyboard interrupt
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Log the exception
    logging.error(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

    # Show user-friendly error message
    if config.debug_mode:
        # Show full traceback in debug mode
        traceback.print_exception(exc_type, exc_value, exc_traceback)
    else:
        # Show simple error message
        click.echo(f"❌ An error occurred: {exc_value}", err=True)
        click.echo("   Run with --debug for more details", err=True)


def install_exception_handler():
    """Install global exception handler"""
    sys.excepthook = handle_exception


class CLIError(Exception):
    """Base exception for CLI errors"""
    def __init__(self, message: str, exit_code: int = 1):
        self.message = message
        self.exit_code = exit_code
        super().__init__(self.message)


class FileDiscoveryError(CLIError):
    """Error during file discovery"""
    pass


class SchemaAnalysisError(CLIError):
    """Error during schema analysis"""
    pass


class MigrationError(CLIError):
    """Error during migration"""
    pass


class ValidationError(CLIError):
    """Error during validation"""
    pass


class RollbackError(CLIError):
    """Error during rollback"""
    pass


def handle_cli_error(error: CLIError):
    """
    Handle CLI-specific errors

    Args:
        error: CLI error instance
    """
    logging.error(f"{error.__class__.__name__}: {error.message}")

    # Show user-friendly message
    click.echo(f"❌ {error.message}", err=True)

    # Exit with appropriate code
    sys.exit(error.exit_code)


def safe_execute(func):
    """
    Decorator for safe command execution with error handling

    Args:
        func: Function to wrap

    Returns:
        Wrapped function
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CLIError as e:
            handle_cli_error(e)
        except click.Abort:
            click.echo("❌ Operation aborted by user", err=True)
            sys.exit(1)
        except Exception as e:
            logging.exception(f"Unexpected error in {func.__name__}")

            if config.debug_mode:
                raise
            else:
                click.echo(f"❌ An unexpected error occurred: {str(e)}", err=True)
                click.echo("   Run with --debug for more details", err=True)
                sys.exit(1)

    return wrapper


def validate_file_path(path: Path, must_exist: bool = True, must_be_file: bool = True):
    """
    Validate file path

    Args:
        path: Path to validate
        must_exist: Whether file must exist
        must_be_file: Whether path must be a file (not directory)

    Raises:
        CLIError: If validation fails
    """
    if must_exist and not path.exists():
        raise CLIError(f"Path does not exist: {path}")

    if must_be_file and path.exists() and not path.is_file():
        raise CLIError(f"Path is not a file: {path}")


def validate_directory_path(path: Path, must_exist: bool = True, must_be_writable: bool = False):
    """
    Validate directory path

    Args:
        path: Path to validate
        must_exist: Whether directory must exist
        must_be_writable: Whether directory must be writable

    Raises:
        CLIError: If validation fails
    """
    if must_exist and not path.exists():
        raise CLIError(f"Directory does not exist: {path}")

    if path.exists() and not path.is_dir():
        raise CLIError(f"Path is not a directory: {path}")

    if must_be_writable and path.exists():
        import os
        if not os.access(path, os.W_OK):
            raise CLIError(f"Directory is not writable: {path}")
