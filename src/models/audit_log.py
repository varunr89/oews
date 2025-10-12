"""
AuditLog Model

Comprehensive audit trail for all system operations and changes.
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import validates
from sqlalchemy.dialects.postgresql import UUID, JSON

from . import Base


class AuditLog(Base):
    """Comprehensive audit trail for all system operations and changes"""

    # Operation identification
    operation_type = Column(
        String(50),
        nullable=False,
        comment="Type of operation: file_discovery, schema_analysis, migration, validation, rollback"
    )

    entity_type = Column(
        String(50),
        nullable=False,
        comment="Type of entity affected: excel_file, migration_batch, validation_report, etc."
    )

    entity_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID of the affected entity"
    )

    # Operation details
    operation_name = Column(
        String(255),
        nullable=False,
        comment="Human-readable operation name"
    )

    operation_status = Column(
        String(20),
        nullable=False,
        comment="Operation result: success, failure, warning"
    )

    # Audit details
    user_context = Column(
        String(255),
        nullable=True,
        comment="User or system context that initiated the operation"
    )

    session_id = Column(
        String(100),
        nullable=True,
        comment="Session or batch ID for grouping related operations"
    )

    # Change tracking
    changes_made = Column(
        JSON,
        nullable=True,
        comment="Detailed list of changes made during the operation"
    )

    old_values = Column(
        JSON,
        nullable=True,
        comment="Previous values before the operation"
    )

    new_values = Column(
        JSON,
        nullable=True,
        comment="New values after the operation"
    )

    # Error and performance tracking
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if operation failed"
    )

    execution_time_ms = Column(
        Integer,
        nullable=True,
        comment="Operation execution time in milliseconds"
    )

    memory_usage_mb = Column(
        Integer,
        nullable=True,
        comment="Peak memory usage during operation in MB"
    )

    # Additional metadata
    operation_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional operation metadata and context"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('file_discovery', 'schema_analysis', 'migration', 'validation', 'rollback', 'system')",
            name="valid_operation_type"
        ),
        CheckConstraint(
            "operation_status IN ('success', 'failure', 'warning', 'in_progress')",
            name="valid_operation_status"
        ),
        CheckConstraint(
            "execution_time_ms IS NULL OR execution_time_ms >= 0",
            name="valid_execution_time"
        ),
        CheckConstraint(
            "memory_usage_mb IS NULL OR memory_usage_mb >= 0",
            name="valid_memory_usage"
        )
    )

    @validates('operation_name')
    def validate_operation_name(self, key: str, operation_name: str) -> str:
        """Validate operation name is not empty"""
        if not operation_name or not operation_name.strip():
            raise ValueError("operation_name cannot be empty")
        return operation_name.strip()

    @classmethod
    def log_operation(cls, operation_type: str, entity_type: str, operation_name: str,
                     status: str, entity_id=None, **kwargs):
        """
        Helper method to create audit log entries

        Args:
            operation_type: Type of operation
            entity_type: Type of entity affected
            operation_name: Human-readable operation name
            status: Operation status
            entity_id: ID of affected entity
            **kwargs: Additional fields like error_message, execution_time_ms, etc.
        """
        return cls(
            operation_type=operation_type,
            entity_type=entity_type,
            entity_id=entity_id,
            operation_name=operation_name,
            operation_status=status,
            **kwargs
        )

    def __repr__(self) -> str:
        return f"<AuditLog(operation='{self.operation_name}', status='{self.operation_status}', entity='{self.entity_type}')>"