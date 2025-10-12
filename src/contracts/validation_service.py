"""
Validation Service Contract

Maps to Functional Requirements:
- FR-008: System MUST execute data consistency checks comparing source Excel data with migrated database data
- FR-009: System MUST validate referential integrity and data relationships after migration
- FR-010: System MUST identify and report any data discrepancies between source and target
"""

from typing import List, Optional, Dict, Any, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
import uuid


class ValidationLevel(Enum):
    BASIC = "basic"
    COMPREHENSIVE = "comprehensive"
    EXHAUSTIVE = "exhaustive"


class ValidationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class ValidationRule:
    """Definition of a validation rule"""
    rule_id: str
    name: str
    description: str
    validation_type: str  # schema, data_integrity, referential_integrity, business_logic
    expression: str  # SQL or Python expression
    severity: str  # error, warning, info
    enabled: bool = True


@dataclass
class ValidationError:
    """Details of a validation error or warning"""
    rule_id: str
    severity: str
    message: str
    table_name: str
    column_name: Optional[str]
    record_identifiers: Dict[str, Any]
    expected_value: Optional[Any]
    actual_value: Optional[Any]
    suggestion: Optional[str]


@dataclass
class ValidationOptions:
    """Configuration options for validation operations"""
    validation_level: ValidationLevel = ValidationLevel.COMPREHENSIVE
    custom_rules: List[ValidationRule] = None
    sample_percentage: float = 100.0  # Percentage of data to validate
    parallel_validation: bool = True
    stop_on_first_error: bool = False
    generate_detailed_report: bool = True

    def __post_init__(self):
        if self.custom_rules is None:
            self.custom_rules = []


@dataclass
class ValidationReport:
    """Complete validation report for a migration operation"""
    batch_id: uuid.UUID
    file_path: Path
    validation_status: ValidationStatus
    start_time: str  # ISO format
    end_time: str  # ISO format
    total_records_validated: int
    total_errors: int
    total_warnings: int
    errors_by_type: Dict[str, int]
    validation_errors: List[ValidationError]
    data_integrity_score: float  # 0.0 to 1.0
    recommendations: List[str]


@dataclass
class SchemaValidationResult:
    """Result of schema validation between source and target"""
    is_compatible: bool
    missing_columns: List[str]
    type_mismatches: List[Tuple[str, str, str]]  # column, source_type, target_type
    constraint_violations: List[str]
    recommendations: List[str]


class ValidationService(ABC):
    """Abstract interface for data validation operations"""

    @abstractmethod
    def validate_schema_compatibility(
        self,
        source_schema: Dict[str, Any],
        target_schema: Dict[str, Any]
    ) -> SchemaValidationResult:
        """
        Validate compatibility between source Excel schema and target database schema

        Args:
            source_schema: Schema definition from Excel analysis
            target_schema: Target database schema definition

        Returns:
            SchemaValidationResult with compatibility analysis

        Raises:
            ValueError: If schema definitions are invalid
        """
        pass

    @abstractmethod
    def validate_data_integrity(
        self,
        batch_id: uuid.UUID,
        options: Optional[ValidationOptions] = None
    ) -> ValidationReport:
        """
        Validate data integrity after migration

        Args:
            batch_id: UUID of the migration batch to validate
            options: Validation configuration options

        Returns:
            ValidationReport with detailed validation results

        Raises:
            ValueError: If batch_id is not found
        """
        pass

    @abstractmethod
    def validate_referential_integrity(
        self,
        table_relationships: Dict[str, List[str]],
        target_schema: str
    ) -> List[ValidationError]:
        """
        Validate referential integrity constraints

        Args:
            table_relationships: Mapping of table to foreign key columns
            target_schema: Target database schema name

        Returns:
            List of ValidationError for constraint violations

        Raises:
            ValueError: If table_relationships format is invalid
        """
        pass

    @abstractmethod
    def compare_source_target_data(
        self,
        source_file: Path,
        target_table: str,
        sample_size: Optional[int] = None
    ) -> List[ValidationError]:
        """
        Compare source Excel data with migrated database data

        Args:
            source_file: Path to the original Excel file
            target_table: Name of the target database table
            sample_size: Number of records to sample for comparison

        Returns:
            List of ValidationError for data discrepancies

        Raises:
            FileNotFoundError: If source file doesn't exist
            ValueError: If target table doesn't exist
        """
        pass

    @abstractmethod
    def validate_business_rules(
        self,
        table_name: str,
        business_rules: List[ValidationRule]
    ) -> List[ValidationError]:
        """
        Validate custom business rules against migrated data

        Args:
            table_name: Name of the table to validate
            business_rules: List of business rule definitions

        Returns:
            List of ValidationError for rule violations

        Raises:
            ValueError: If table_name is invalid or rules are malformed
        """
        pass

    @abstractmethod
    def generate_validation_summary(
        self,
        batch_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Generate summary statistics for validation results

        Args:
            batch_id: UUID of the migration batch

        Returns:
            Dictionary with validation summary statistics

        Raises:
            ValueError: If batch_id is not found
        """
        pass

    @abstractmethod
    def create_validation_checkpoint(
        self,
        batch_id: uuid.UUID,
        checkpoint_name: str
    ) -> str:
        """
        Create a validation checkpoint for incremental validation

        Args:
            batch_id: UUID of the migration batch
            checkpoint_name: Name for the checkpoint

        Returns:
            Checkpoint identifier string

        Raises:
            ValueError: If parameters are invalid
        """
        pass

    @abstractmethod
    def validate_duplicate_detection(
        self,
        table_name: str,
        primary_key_columns: List[str]
    ) -> List[ValidationError]:
        """
        Validate that duplicate detection worked correctly

        Args:
            table_name: Name of the table to check
            primary_key_columns: Columns that define uniqueness

        Returns:
            List of ValidationError for unexpected duplicates

        Raises:
            ValueError: If table_name or primary_key_columns are invalid
        """
        pass

    @abstractmethod
    def validate_data_types(
        self,
        table_name: str,
        expected_schema: Dict[str, str]
    ) -> List[ValidationError]:
        """
        Validate that data types were converted correctly

        Args:
            table_name: Name of the table to validate
            expected_schema: Expected column types

        Returns:
            List of ValidationError for type conversion issues

        Raises:
            ValueError: If table_name is invalid
        """
        pass

    @abstractmethod
    def export_validation_report(
        self,
        validation_report: ValidationReport,
        output_format: str,
        output_path: Path
    ) -> bool:
        """
        Export validation report to file

        Args:
            validation_report: ValidationReport to export
            output_format: Export format (json, csv, html, pdf)
            output_path: Path for the exported report

        Returns:
            True if export successful, False otherwise

        Raises:
            ValueError: If output_format is unsupported
        """
        pass