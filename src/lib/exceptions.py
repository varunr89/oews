"""
Exception Hierarchy

Custom exceptions for OEWS migration application.
"""


class OEWSException(Exception):
    """Base exception for OEWS migration application"""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# File Discovery Exceptions
class FileDiscoveryException(OEWSException):
    """Exception during file discovery"""
    pass


class FileAccessException(FileDiscoveryException):
    """Exception when file cannot be accessed"""
    pass


class InvalidFileFormatException(FileDiscoveryException):
    """Exception when file format is invalid"""
    pass


# Schema Analysis Exceptions
class SchemaAnalysisException(OEWSException):
    """Exception during schema analysis"""
    pass


class SchemaConflictException(SchemaAnalysisException):
    """Exception when schemas conflict"""
    pass


class InvalidSchemaException(SchemaAnalysisException):
    """Exception when schema is invalid"""
    pass


# Migration Exceptions
class MigrationException(OEWSException):
    """Exception during migration"""
    pass


class BatchCreationException(MigrationException):
    """Exception when creating migration batch"""
    pass


class RecordProcessingException(MigrationException):
    """Exception when processing records"""
    pass


class DuplicateRecordException(MigrationException):
    """Exception when duplicate record is found"""
    pass


class TypeConversionException(MigrationException):
    """Exception during type conversion"""
    pass


# Validation Exceptions
class ValidationException(OEWSException):
    """Exception during validation"""
    pass


class DataIntegrityException(ValidationException):
    """Exception when data integrity check fails"""
    pass


class ReferentialIntegrityException(ValidationException):
    """Exception when referential integrity check fails"""
    pass


# Rollback Exceptions
class RollbackException(OEWSException):
    """Exception during rollback"""
    pass


class CheckpointNotFoundException(RollbackException):
    """Exception when rollback checkpoint not found"""
    pass


class RollbackFailedException(RollbackException):
    """Exception when rollback operation fails"""
    pass


# Database Exceptions
class DatabaseException(OEWSException):
    """Exception related to database operations"""
    pass


class ConnectionException(DatabaseException):
    """Exception when database connection fails"""
    pass


class QueryException(DatabaseException):
    """Exception when database query fails"""
    pass


class TransactionException(DatabaseException):
    """Exception during transaction"""
    pass


# Configuration Exceptions
class ConfigurationException(OEWSException):
    """Exception related to configuration"""
    pass


class InvalidConfigurationException(ConfigurationException):
    """Exception when configuration is invalid"""
    pass


class MissingConfigurationException(ConfigurationException):
    """Exception when required configuration is missing"""
    pass


# Performance Exceptions
class PerformanceException(OEWSException):
    """Exception related to performance constraints"""
    pass


class MemoryLimitException(PerformanceException):
    """Exception when memory limit is exceeded"""
    pass


class TimeoutException(PerformanceException):
    """Exception when operation times out"""
    pass


# Utility functions
def format_exception_details(exception: OEWSException) -> str:
    """
    Format exception details for logging

    Args:
        exception: OEWS exception instance

    Returns:
        Formatted string with exception details
    """
    details_str = f"{exception.__class__.__name__}: {exception.message}"

    if exception.details:
        details_list = [f"  {k}: {v}" for k, v in exception.details.items()]
        details_str += "\nDetails:\n" + "\n".join(details_list)

    return details_str


def wrap_exception(original_exception: Exception, context: str) -> OEWSException:
    """
    Wrap a generic exception in an OEWS exception

    Args:
        original_exception: Original exception
        context: Context describing where the exception occurred

    Returns:
        Wrapped OEWS exception
    """
    message = f"{context}: {str(original_exception)}"
    details = {
        'original_exception': original_exception.__class__.__name__,
        'original_message': str(original_exception)
    }

    return OEWSException(message, details)
