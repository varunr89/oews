"""
ValidationReport Model

Stores comprehensive validation results for migration operations.
"""

from typing import Optional

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID, JSON

from . import Base, ValidationStatus


class ValidationReport(Base):
    """Stores comprehensive validation results for migration operations"""

    # Parent relationship
    migration_record_id = Column(
        UUID(as_uuid=True),
        ForeignKey('migration_record.id', ondelete='CASCADE'),
        nullable=False,
        comment="Foreign key to MigrationRecord"
    )

    # Report metadata
    validation_type = Column(
        String(50),
        nullable=False,
        comment="Type of validation: schema, data_integrity, referential_integrity, business_rules"
    )

    # Timing
    start_time = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Validation start timestamp"
    )

    end_time = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Validation completion timestamp"
    )

    # Status and results
    validation_status = Column(
        String(20),
        nullable=False,
        default=ValidationStatus.PENDING,
        comment="Validation result status"
    )

    # Validation metrics
    total_records_validated = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of records validated"
    )

    total_errors = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of validation errors found"
    )

    total_warnings = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of validation warnings found"
    )

    data_integrity_score = Column(
        Float,
        nullable=True,
        comment="Data integrity score (0.0-1.0)"
    )

    # Detailed results
    errors_by_type = Column(
        JSON,
        nullable=True,
        comment="Error counts by category"
    )

    validation_errors = Column(
        JSON,
        nullable=True,
        comment="Detailed validation error list"
    )

    recommendations = Column(
        JSON,
        nullable=True,
        comment="Recommendations for data quality improvement"
    )

    # Report summary
    summary = Column(
        Text,
        nullable=True,
        comment="Human-readable validation summary"
    )

    # Relationships
    migration_record = relationship(
        "MigrationRecord",
        back_populates="validation_reports"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "validation_status IN ('pending', 'running', 'passed', 'failed', 'warning')",
            name="valid_validation_status"
        ),
        CheckConstraint(
            "validation_type IN ('schema', 'data_integrity', 'referential_integrity', 'business_rules')",
            name="valid_validation_type"
        ),
        CheckConstraint(
            "total_records_validated >= 0",
            name="valid_total_records_validated"
        ),
        CheckConstraint(
            "total_errors >= 0",
            name="valid_total_errors"
        ),
        CheckConstraint(
            "total_warnings >= 0",
            name="valid_total_warnings"
        ),
        CheckConstraint(
            "data_integrity_score IS NULL OR (data_integrity_score >= 0.0 AND data_integrity_score <= 1.0)",
            name="valid_data_integrity_score"
        )
    )

    def get_validation_duration(self) -> Optional[float]:
        """Get validation duration in seconds"""
        if not self.start_time or not self.end_time:
            return None
        return (self.end_time - self.start_time).total_seconds()

    def __repr__(self) -> str:
        return f"<ValidationReport(type='{self.validation_type}', status='{self.validation_status}', errors={self.total_errors})>"