"""
Migration Engine Service Contract

Maps to Functional Requirements:
- FR-004: System MUST migrate all data records from Excel files to the SQL database while preserving data integrity
- FR-005: System MUST perform data type conversion between Excel formats and SQL database types
- FR-006: System MUST skip invalid or corrupted data records during migration and continue processing valid records
- FR-011: System MUST skip duplicate records after the first occurrence during migration
- FR-012: System MUST provide per-file rollback capability to undo migration of individual Excel files
- FR-014: System MUST support incremental migrations for new Excel files and overwrite existing records with updated data from newer files
"""

from typing import List, Optional, Dict, Any, Iterator
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
import uuid


class MigrationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ConflictResolution(Enum):
    SKIP_DUPLICATE = "skip_duplicate"
    OVERWRITE_EXISTING = "overwrite_existing"
    CREATE_VERSION = "create_version"
    FAIL_ON_CONFLICT = "fail_on_conflict"


@dataclass
class MigrationOptions:
    """Configuration options for migration operations"""
    batch_size: int = 10000
    max_memory_usage: int = 1073741824  # 1GB
    conflict_resolution: ConflictResolution = ConflictResolution.SKIP_DUPLICATE
    enable_rollback: bool = True
    validate_data: bool = True
    skip_invalid_records: bool = True
    preserve_source_metadata: bool = True


@dataclass
class MigrationProgress:
    """Real-time migration progress information"""
    batch_id: uuid.UUID
    file_path: Path
    total_records: int
    processed_records: int
    skipped_records: int
    failed_records: int
    current_status: MigrationStatus
    start_time: str  # ISO format
    estimated_completion: Optional[str] = None  # ISO format
    current_operation: str = ""


@dataclass
class MigrationResult:
    """Result of a file migration operation"""
    batch_id: uuid.UUID
    file_path: Path
    status: MigrationStatus
    records_processed: int
    records_skipped: int
    records_failed: int
    validation_errors: List[str]
    rollback_checkpoint: Optional[str]
    execution_time: float  # seconds
    memory_peak: int  # bytes


@dataclass
class RollbackInfo:
    """Information needed for rollback operations"""
    batch_id: uuid.UUID
    file_path: Path
    rollback_checkpoint: str
    affected_tables: List[str]
    record_count: int
    rollback_data: Dict[str, Any]


class MigrationEngineService(ABC):
    """Abstract interface for data migration operations"""

    @abstractmethod
    def start_migration_batch(
        self,
        excel_files: List[Path],
        target_schema: str,
        options: Optional[MigrationOptions] = None
    ) -> uuid.UUID:
        """
        Start a new migration batch for multiple Excel files

        Args:
            excel_files: List of Excel files to migrate
            target_schema: Target database schema name
            options: Migration configuration options

        Returns:
            UUID of the created migration batch

        Raises:
            ValueError: If target_schema is invalid or files are inaccessible
        """
        pass

    @abstractmethod
    def migrate_single_file(
        self,
        file_path: Path,
        target_schema: str,
        batch_id: Optional[uuid.UUID] = None,
        options: Optional[MigrationOptions] = None
    ) -> MigrationResult:
        """
        Migrate a single Excel file to the database

        Args:
            file_path: Path to the Excel file
            target_schema: Target database schema name
            batch_id: Optional batch ID for grouping
            options: Migration configuration options

        Returns:
            MigrationResult with operation details

        Raises:
            FileNotFoundError: If Excel file doesn't exist
            ValueError: If file format is unsupported
        """
        pass

    @abstractmethod
    def get_migration_progress(self, batch_id: uuid.UUID) -> List[MigrationProgress]:
        """
        Get real-time progress for a migration batch

        Args:
            batch_id: UUID of the migration batch

        Returns:
            List of MigrationProgress for each file in the batch

        Raises:
            ValueError: If batch_id is not found
        """
        pass

    @abstractmethod
    def pause_migration(self, batch_id: uuid.UUID) -> bool:
        """
        Pause an ongoing migration batch

        Args:
            batch_id: UUID of the migration batch

        Returns:
            True if successfully paused, False otherwise
        """
        pass

    @abstractmethod
    def resume_migration(self, batch_id: uuid.UUID) -> bool:
        """
        Resume a paused migration batch

        Args:
            batch_id: UUID of the migration batch

        Returns:
            True if successfully resumed, False otherwise
        """
        pass

    @abstractmethod
    def rollback_file_migration(
        self,
        file_path: Path,
        rollback_checkpoint: str
    ) -> bool:
        """
        Rollback migration for a specific file

        Args:
            file_path: Path to the original Excel file
            rollback_checkpoint: Checkpoint identifier for rollback

        Returns:
            True if rollback successful, False otherwise

        Raises:
            ValueError: If rollback_checkpoint is invalid
        """
        pass

    @abstractmethod
    def rollback_batch_migration(self, batch_id: uuid.UUID) -> List[RollbackInfo]:
        """
        Rollback entire migration batch

        Args:
            batch_id: UUID of the migration batch

        Returns:
            List of RollbackInfo for each file rolled back

        Raises:
            ValueError: If batch_id is not found
        """
        pass

    @abstractmethod
    def process_record_batch(
        self,
        records: Iterator[Dict[str, Any]],
        table_mapping: Dict[str, str],
        options: MigrationOptions
    ) -> Dict[str, int]:
        """
        Process a batch of records with type conversion and validation

        Args:
            records: Iterator of record dictionaries
            table_mapping: Mapping from source columns to target columns
            options: Migration configuration options

        Returns:
            Dictionary with counts: processed, skipped, failed

        Raises:
            ValueError: If table_mapping is invalid
        """
        pass

    @abstractmethod
    def detect_and_handle_duplicates(
        self,
        records: List[Dict[str, Any]],
        primary_key_columns: List[str],
        conflict_resolution: ConflictResolution
    ) -> List[Dict[str, Any]]:
        """
        Detect and handle duplicate records based on conflict resolution strategy

        Args:
            records: List of record dictionaries to check
            primary_key_columns: Columns that define uniqueness
            conflict_resolution: Strategy for handling conflicts

        Returns:
            List of processed records after duplicate handling
        """
        pass

    @abstractmethod
    def create_rollback_checkpoint(
        self,
        file_path: Path,
        table_name: str
    ) -> str:
        """
        Create a checkpoint for potential rollback operations

        Args:
            file_path: Path to the source Excel file
            table_name: Target database table name

        Returns:
            Checkpoint identifier string

        Raises:
            ValueError: If parameters are invalid
        """
        pass