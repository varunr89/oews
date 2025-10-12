"""
SQLAlchemy Base Model and Common Utilities

This module provides the base model class and common functionality
for all OEWS migration application models.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, String, DateTime, MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.sql import func

# Create metadata with naming convention for constraints
# This ensures consistent constraint naming across different databases
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class BaseModel:
    """
    Base model class providing common fields and functionality

    All model classes should inherit from this base to ensure
    consistent timestamp tracking and UUID primary keys.
    """

    @declared_attr
    def __tablename__(cls):
        """Generate table name from class name (convert CamelCase to snake_case)"""
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    # Primary key as UUID
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier"
    )

    # Audit timestamp fields
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp"
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp"
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary

        Returns:
            Dictionary representation of the model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Handle UUID and datetime serialization
            if isinstance(value, uuid.UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update model instance from dictionary

        Args:
            data: Dictionary with field values to update
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """
        Create model instance from dictionary

        Args:
            data: Dictionary with field values

        Returns:
            New model instance
        """
        # Filter out fields that don't exist on the model
        valid_fields = {
            key: value for key, value in data.items()
            if hasattr(cls, key)
        }
        return cls(**valid_fields)

    def __repr__(self) -> str:
        """String representation of the model"""
        return f"<{self.__class__.__name__}(id={self.id})>"


# Create the declarative base using our metadata and base class
Base = declarative_base(cls=BaseModel, metadata=metadata)


# Common enum definitions used across multiple models
class FileStatus:
    """Status values for Excel file processing"""
    DISCOVERED = "discovered"
    ANALYZING = "analyzing"
    MIGRATING = "migrating"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationStatus:
    """Status values for migration operations"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ValidationStatus:
    """Status values for validation operations"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


class ExcelDataType:
    """Excel data type classifications"""
    TEXT = "text"
    NUMERIC = "numeric"
    DATE = "date"
    BOOLEAN = "boolean"
    FORMULA = "formula"


class SQLDataType:
    """SQL data type mappings"""
    VARCHAR = "varchar"
    TEXT = "text"
    INTEGER = "integer"
    BIGINT = "bigint"
    DECIMAL = "decimal"
    FLOAT = "float"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    BOOLEAN = "boolean"
    JSON = "json"


# Import all models to ensure they are registered with SQLAlchemy
from .excel_file import ExcelFile
from .excel_sheet import ExcelSheet
from .column_definition import ColumnDefinition
from .unified_schema import UnifiedSchema
from .table_definition import TableDefinition
from .column_mapping import ColumnMapping
from .migration_batch import MigrationBatch
from .migration_record import MigrationRecord
from .validation_report import ValidationReport
from .audit_log import AuditLog

# Export public interface
__all__ = [
    'Base',
    'BaseModel',
    'metadata',
    'FileStatus',
    'MigrationStatus',
    'ValidationStatus',
    'ExcelDataType',
    'SQLDataType',
    'ExcelFile',
    'ExcelSheet',
    'ColumnDefinition',
    'UnifiedSchema',
    'TableDefinition',
    'ColumnMapping',
    'MigrationBatch',
    'MigrationRecord',
    'ValidationReport',
    'AuditLog'
]