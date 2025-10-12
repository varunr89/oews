"""
MigrationBatch Model

Groups related migration operations for tracking and rollback.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID, JSON

from . import Base, MigrationStatus


class MigrationBatch(Base):
    """Groups related migration operations for tracking and rollback"""

    # Parent relationship
    unified_schema_id = Column(
        UUID(as_uuid=True),
        ForeignKey('unified_schema.id', ondelete='CASCADE'),
        nullable=False,
        comment="Foreign key to UnifiedSchema"
    )

    # Batch identification
    batch_name = Column(
        String(255),
        nullable=False,
        comment="Descriptive name for the migration batch"
    )

    # Timing
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Migration start timestamp"
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Migration completion timestamp"
    )

    # Status tracking
    status = Column(
        String(20),
        nullable=False,
        default=MigrationStatus.PENDING,
        comment="Current batch status"
    )

    # Counters
    total_files = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of files in the batch"
    )

    processed_files = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of successfully processed files"
    )

    failed_files = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of failed files"
    )

    total_records = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total records migrated"
    )

    # Error tracking
    error_summary = Column(
        JSON,
        nullable=True,
        comment="Summary of errors encountered"
    )

    # Relationships
    unified_schema = relationship(
        "UnifiedSchema",
        back_populates="migration_batches"
    )

    migration_records = relationship(
        "MigrationRecord",
        back_populates="migration_batch",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'rolled_back')",
            name="valid_status"
        ),
        CheckConstraint(
            "total_files >= 0",
            name="valid_total_files"
        ),
        CheckConstraint(
            "processed_files >= 0",
            name="valid_processed_files"
        ),
        CheckConstraint(
            "failed_files >= 0",
            name="valid_failed_files"
        ),
        CheckConstraint(
            "total_records >= 0",
            name="valid_total_records"
        ),
        CheckConstraint(
            "processed_files + failed_files <= total_files",
            name="valid_file_counts"
        )
    )

    @validates('batch_name')
    def validate_batch_name(self, key: str, batch_name: str) -> str:
        """Validate batch name is not empty"""
        if not batch_name or not batch_name.strip():
            raise ValueError("batch_name cannot be empty")
        return batch_name.strip()

    def get_processing_duration(self) -> Optional[float]:
        """Get total processing duration in seconds"""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    def __repr__(self) -> str:
        return f"<MigrationBatch(batch_name='{self.batch_name}', status='{self.status}', files={self.total_files})>"