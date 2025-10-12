"""
MigrationRecord Model

Tracks individual file migration operations within a batch.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID, JSON

from . import Base, MigrationStatus


class MigrationRecord(Base):
    """Tracks individual file migration operations within a batch"""

    # Parent relationships
    migration_batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey('migration_batch.id', ondelete='CASCADE'),
        nullable=False,
        comment="Foreign key to MigrationBatch"
    )

    excel_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey('excel_file.id', ondelete='CASCADE'),
        nullable=False,
        comment="Foreign key to ExcelFile"
    )

    # Timing
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="File migration start timestamp"
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="File migration completion timestamp"
    )

    # Status tracking
    status = Column(
        String(20),
        nullable=False,
        default=MigrationStatus.PENDING,
        comment="Current migration status"
    )

    # Record counters
    records_processed = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of records migrated from this file"
    )

    records_skipped = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of invalid/duplicate records skipped"
    )

    records_failed = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of records that failed migration"
    )

    # Error and validation tracking
    validation_errors = Column(
        JSON,
        nullable=True,
        comment="Detailed validation error information"
    )

    rollback_data = Column(
        JSON,
        nullable=True,
        comment="Information needed for rollback operations"
    )

    # Relationships
    migration_batch = relationship(
        "MigrationBatch",
        back_populates="migration_records"
    )

    excel_file = relationship(
        "ExcelFile",
        back_populates="migration_records"
    )

    validation_reports = relationship(
        "ValidationReport",
        back_populates="migration_record",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'analyzing', 'migrating', 'completed', 'failed', 'rolled_back')",
            name="valid_status"
        ),
        CheckConstraint(
            "records_processed >= 0",
            name="valid_records_processed"
        ),
        CheckConstraint(
            "records_skipped >= 0",
            name="valid_records_skipped"
        ),
        CheckConstraint(
            "records_failed >= 0",
            name="valid_records_failed"
        )
    )

    def get_processing_duration(self) -> Optional[float]:
        """Get processing duration in seconds"""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    def get_total_records(self) -> int:
        """Get total records processed (successful + skipped + failed)"""
        return self.records_processed + self.records_skipped + self.records_failed

    def __repr__(self) -> str:
        return f"<MigrationRecord(status='{self.status}', processed={self.records_processed})>"