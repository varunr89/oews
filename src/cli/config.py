"""
Configuration Management

Handles application configuration with environment variable support.
Provides centralized access to configuration settings.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Any, Dict
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """
    Configuration management with environment variable handling

    Loads configuration from environment variables and .env files.
    Provides type-safe access to configuration values with defaults.
    """

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration

        Args:
            env_file: Path to .env file (optional, defaults to .env in current directory)
        """
        # Load .env file if it exists
        if env_file:
            env_path = Path(env_file)
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded configuration from {env_file}")
        else:
            # Try to load from default locations
            default_paths = [Path('.env'), Path('.env.local')]
            for path in default_paths:
                if path.exists():
                    load_dotenv(path)
                    logger.info(f"Loaded configuration from {path}")
                    break

    # Database Configuration
    @property
    def database_url(self) -> str:
        """
        Get database URL

        Returns:
            Database connection URL
        """
        return os.getenv('DATABASE_URL', 'sqlite:///oews_migration.db')

    @property
    def database_pool_size(self) -> int:
        """
        Get database connection pool size

        Returns:
            Connection pool size
        """
        return int(os.getenv('DATABASE_POOL_SIZE', '5'))

    @property
    def database_max_overflow(self) -> int:
        """
        Get database max overflow connections

        Returns:
            Max overflow connections
        """
        return int(os.getenv('DATABASE_MAX_OVERFLOW', '10'))

    # Logging Configuration
    @property
    def log_level(self) -> str:
        """
        Get logging level

        Returns:
            Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        return os.getenv('LOG_LEVEL', 'INFO').upper()

    @property
    def log_file(self) -> Optional[str]:
        """
        Get log file path

        Returns:
            Path to log file or None for console-only logging
        """
        return os.getenv('LOG_FILE')

    @property
    def log_format(self) -> str:
        """
        Get log format

        Returns:
            Log format string
        """
        return os.getenv(
            'LOG_FORMAT',
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # Performance Configuration
    @property
    def max_memory_usage(self) -> int:
        """
        Get maximum memory usage in MB

        Returns:
            Maximum memory usage in megabytes
        """
        # Default to 1.75GB (1792 MB) per constitutional requirements
        return int(os.getenv('MAX_MEMORY_USAGE', '1792'))

    @property
    def batch_size(self) -> int:
        """
        Get batch size for data processing

        Returns:
            Number of records to process per batch
        """
        return int(os.getenv('BATCH_SIZE', '1000'))

    @property
    def query_timeout(self) -> int:
        """
        Get database query timeout in seconds

        Returns:
            Query timeout in seconds
        """
        return int(os.getenv('QUERY_TIMEOUT', '30'))

    # Migration Configuration
    @property
    def data_directory(self) -> str:
        """
        Get data directory path

        Returns:
            Path to data directory
        """
        return os.getenv('DATA_DIRECTORY', 'data')

    @property
    def output_directory(self) -> str:
        """
        Get output directory for migration results

        Returns:
            Path to output directory
        """
        return os.getenv('OUTPUT_DIRECTORY', 'output')

    @property
    def log_directory(self) -> str:
        """
        Get log directory path

        Returns:
            Path to log directory
        """
        return os.getenv('LOG_DIRECTORY', 'logs')

    @property
    def enable_validation(self) -> bool:
        """
        Check if validation is enabled

        Returns:
            True if validation should be performed
        """
        return os.getenv('ENABLE_VALIDATION', 'true').lower() in ('true', '1', 'yes')

    @property
    def enable_rollback(self) -> bool:
        """
        Check if rollback is enabled

        Returns:
            True if rollback capability is enabled
        """
        return os.getenv('ENABLE_ROLLBACK', 'true').lower() in ('true', '1', 'yes')

    # Excel Processing Configuration
    @property
    def excel_engine(self) -> str:
        """
        Get Excel engine to use

        Returns:
            Excel engine name (openpyxl, xlrd, etc.)
        """
        return os.getenv('EXCEL_ENGINE', 'openpyxl')

    @property
    def max_file_size_mb(self) -> int:
        """
        Get maximum Excel file size in MB

        Returns:
            Maximum file size in megabytes
        """
        return int(os.getenv('MAX_FILE_SIZE_MB', '100'))

    @property
    def skip_empty_sheets(self) -> bool:
        """
        Check if empty sheets should be skipped

        Returns:
            True if empty sheets should be skipped
        """
        return os.getenv('SKIP_EMPTY_SHEETS', 'true').lower() in ('true', '1', 'yes')

    # Application Configuration
    @property
    def debug_mode(self) -> bool:
        """
        Check if debug mode is enabled

        Returns:
            True if debug mode is enabled
        """
        return os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes')

    @property
    def environment(self) -> str:
        """
        Get application environment

        Returns:
            Environment name (development, production, test)
        """
        return os.getenv('ENVIRONMENT', 'development').lower()

    # Helper Methods
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return os.getenv(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value

        Args:
            key: Configuration key
            value: Configuration value
        """
        os.environ[key] = str(value)
        logger.debug(f"Set configuration: {key} = {value}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Export all configuration as dictionary

        Returns:
            Dictionary containing all configuration values
        """
        return {
            # Database
            'database_url': self.database_url,
            'database_pool_size': self.database_pool_size,
            'database_max_overflow': self.database_max_overflow,

            # Logging
            'log_level': self.log_level,
            'log_file': self.log_file,
            'log_format': self.log_format,

            # Performance
            'max_memory_usage': self.max_memory_usage,
            'batch_size': self.batch_size,
            'query_timeout': self.query_timeout,

            # Migration
            'data_directory': self.data_directory,
            'output_directory': self.output_directory,
            'log_directory': self.log_directory,
            'enable_validation': self.enable_validation,
            'enable_rollback': self.enable_rollback,

            # Excel Processing
            'excel_engine': self.excel_engine,
            'max_file_size_mb': self.max_file_size_mb,
            'skip_empty_sheets': self.skip_empty_sheets,

            # Application
            'debug_mode': self.debug_mode,
            'environment': self.environment,
        }

    def validate(self) -> bool:
        """
        Validate configuration

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Check required values
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")

        # Validate log level
        valid_log_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if self.log_level not in valid_log_levels:
            raise ValueError(f"Invalid LOG_LEVEL: {self.log_level}. Must be one of {valid_log_levels}")

        # Validate numeric ranges
        if self.max_memory_usage <= 0:
            raise ValueError("MAX_MEMORY_USAGE must be positive")

        if self.batch_size <= 0:
            raise ValueError("BATCH_SIZE must be positive")

        if self.query_timeout <= 0:
            raise ValueError("QUERY_TIMEOUT must be positive")

        if self.max_file_size_mb <= 0:
            raise ValueError("MAX_FILE_SIZE_MB must be positive")

        logger.info("Configuration validation passed")
        return True


# Global configuration instance
config = Config()
