"""
ExcelFile Model

Represents an OEWS Excel file being processed for migration.
Maps to Functional Requirements FR-001 (file discovery and enumeration).
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy import Column, String, Integer, DateTime, Boolean, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID

from . import Base, FileStatus


class ExcelFile(Base):
    """
    Represents an OEWS Excel file being processed for migration

    This model tracks individual Excel files throughout the migration process,
    from discovery through completion, with full audit trail and status tracking.
    """

    # File identification and location
    file_path = Column(
        String(500),
        nullable=False,
        unique=True,
        comment="Absolute path to the Excel file"
    )

    file_name = Column(
        String(255),
        nullable=False,
        comment="Base name of the file"
    )

    # File metadata
    file_size = Column(
        Integer,
        nullable=False,
        comment="Size in bytes"
    )

    file_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        comment="SHA-256 hash for change detection"
    )

    sheet_count = Column(
        Integer,
        nullable=True,
        comment="Number of worksheets in the file"
    )

    # File timestamps
    file_created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="File creation timestamp from filesystem"
    )

    file_modified_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="File last modification timestamp from filesystem"
    )

    # Processing tracking
    processed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When migration processing began"
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When migration processing completed"
    )

    status = Column(
        String(20),
        nullable=False,
        default=FileStatus.DISCOVERED,
        comment="Current processing status"
    )

    # Error tracking
    error_message = Column(
        String(1000),
        nullable=True,
        comment="Error message if processing failed"
    )

    # Processing metadata
    is_oews_format = Column(
        Boolean,
        nullable=True,
        comment="Whether file matches expected OEWS format"
    )

    oews_year = Column(
        Integer,
        nullable=True,
        comment="OEWS data year extracted from filename or content"
    )

    # Relationships
    excel_sheets = relationship(
        "ExcelSheet",
        back_populates="excel_file",
        cascade="all, delete-orphan",
        lazy="select"
    )

    migration_records = relationship(
        "MigrationRecord",
        back_populates="excel_file",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "file_size > 0 AND file_size <= 104857600",  # 100MB max
            name="valid_file_size"
        ),
        CheckConstraint(
            "status IN ('discovered', 'analyzing', 'migrating', 'completed', 'failed', 'rolled_back')",
            name="valid_status"
        ),
        CheckConstraint(
            "sheet_count IS NULL OR sheet_count >= 0",
            name="valid_sheet_count"
        ),
        CheckConstraint(
            "oews_year IS NULL OR (oews_year >= 2000 AND oews_year <= 2030)",
            name="valid_oews_year"
        ),
        CheckConstraint(
            "completed_at IS NULL OR processed_at IS NULL OR completed_at >= processed_at",
            name="valid_processing_timeline"
        )
    )

    @validates('file_path')
    def validate_file_path(self, key: str, file_path: str) -> str:
        """Validate that file_path is an absolute path"""
        if not os.path.isabs(file_path):
            raise ValueError("file_path must be an absolute path")
        return file_path

    @validates('file_name')
    def validate_file_name(self, key: str, file_name: str) -> str:
        """Validate that file_name is not empty and has valid extension"""
        if not file_name or not file_name.strip():
            raise ValueError("file_name cannot be empty")

        valid_extensions = ['.xls', '.xlsx']
        if not any(file_name.lower().endswith(ext) for ext in valid_extensions):
            raise ValueError(f"file_name must have one of these extensions: {valid_extensions}")

        return file_name.strip()

    @validates('file_hash')
    def validate_file_hash(self, key: str, file_hash: str) -> str:
        """Validate that file_hash is a valid SHA-256 hash"""
        if not file_hash or len(file_hash) != 64:
            raise ValueError("file_hash must be a 64-character SHA-256 hash")

        try:
            int(file_hash, 16)  # Verify it's a valid hex string
        except ValueError:
            raise ValueError("file_hash must be a valid hexadecimal string")

        return file_hash.lower()

    @validates('status')
    def validate_status(self, key: str, status: str) -> str:
        """Validate status transitions"""
        valid_statuses = [
            FileStatus.DISCOVERED,
            FileStatus.ANALYZING,
            FileStatus.MIGRATING,
            FileStatus.COMPLETED,
            FileStatus.FAILED,
            FileStatus.ROLLED_BACK
        ]

        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

        return status

    def get_file_path_obj(self) -> Path:
        """Get file path as Path object"""
        return Path(self.file_path)

    def exists(self) -> bool:
        """Check if the file still exists on filesystem"""
        return self.get_file_path_obj().exists()

    def get_file_stats(self) -> Optional[os.stat_result]:
        """Get current file statistics from filesystem"""
        try:
            return self.get_file_path_obj().stat()
        except (OSError, FileNotFoundError):
            return None

    def is_file_changed(self) -> bool:
        """
        Check if file has been modified since last recorded

        Returns:
            True if file has been modified, False otherwise
        """
        stats = self.get_file_stats()
        if not stats:
            return True  # File no longer exists, consider it changed

        # Check if modification time changed
        file_mtime = datetime.fromtimestamp(stats.st_mtime)
        if self.file_modified_at and file_mtime != self.file_modified_at:
            return True

        # Check if file size changed
        if stats.st_size != self.file_size:
            return True

        return False

    def update_status(self, new_status: str, error_message: Optional[str] = None) -> None:
        """
        Update file processing status with appropriate timestamps

        Args:
            new_status: New status value
            error_message: Optional error message for failed status
        """
        old_status = self.status
        self.status = new_status

        # Set timestamps based on status transitions
        if new_status == FileStatus.MIGRATING and old_status != FileStatus.MIGRATING:
            self.processed_at = datetime.utcnow()
        elif new_status in [FileStatus.COMPLETED, FileStatus.FAILED, FileStatus.ROLLED_BACK]:
            if not self.processed_at:
                self.processed_at = datetime.utcnow()
            self.completed_at = datetime.utcnow()

        # Set error message for failed status
        if new_status == FileStatus.FAILED and error_message:
            self.error_message = error_message
        elif new_status != FileStatus.FAILED:
            self.error_message = None

    def get_processing_duration(self) -> Optional[float]:
        """
        Get total processing duration in seconds

        Returns:
            Duration in seconds, or None if processing not completed
        """
        if not self.processed_at or not self.completed_at:
            return None

        return (self.completed_at - self.processed_at).total_seconds()

    def is_processing_complete(self) -> bool:
        """Check if file processing is complete (success or failure)"""
        return self.status in [
            FileStatus.COMPLETED,
            FileStatus.FAILED,
            FileStatus.ROLLED_BACK
        ]

    def can_rollback(self) -> bool:
        """Check if file migration can be rolled back"""
        return self.status in [FileStatus.COMPLETED, FileStatus.FAILED]

    def __repr__(self) -> str:
        """String representation of the ExcelFile"""
        return f"<ExcelFile(file_name='{self.file_name}', status='{self.status}', size={self.file_size})>"