"""
ExcelSheet Model

Represents individual worksheets within an Excel file.
Maps to schema analysis and data structure requirements.
"""

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID, JSON

from . import Base


class ExcelSheet(Base):
    """
    Represents individual worksheets within an Excel file

    This model tracks worksheet-level metadata including structure,
    schema, and data organization for migration planning.
    """

    # Parent relationship
    excel_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey('excel_file.id', ondelete='CASCADE'),
        nullable=False,
        comment="Foreign key to ExcelFile"
    )

    # Sheet identification
    sheet_name = Column(
        String(255),
        nullable=False,
        comment="Name of the worksheet"
    )

    sheet_index = Column(
        Integer,
        nullable=False,
        comment="Zero-based index within the workbook"
    )

    # Sheet structure
    row_count = Column(
        Integer,
        nullable=True,
        comment="Total number of data rows"
    )

    column_count = Column(
        Integer,
        nullable=True,
        comment="Total number of columns"
    )

    header_row = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Row number containing column headers"
    )

    data_start_row = Column(
        Integer,
        nullable=False,
        default=1,
        comment="First row containing actual data"
    )

    has_header = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether the sheet has column headers"
    )

    # Schema and analysis results
    inferred_schema = Column(
        JSON,
        nullable=True,
        comment="Detected column types and relationships as JSON"
    )

    # OEWS-specific metadata
    is_data_sheet = Column(
        Boolean,
        nullable=True,
        comment="Whether this is the main data sheet (vs metadata sheet)"
    )

    oews_sheet_type = Column(
        String(50),
        nullable=True,
        comment="Type of OEWS sheet: data, field_descriptions, update_time, filler"
    )

    # Data quality metrics
    empty_rows = Column(
        Integer,
        nullable=True,
        comment="Number of completely empty rows"
    )

    empty_columns = Column(
        Integer,
        nullable=True,
        comment="Number of completely empty columns"
    )

    data_density = Column(
        String(10),  # Store as percentage string like "85.3%"
        nullable=True,
        comment="Percentage of cells with data"
    )

    # Analysis metadata
    analyzed_at = Column(
        String(30),  # ISO datetime string
        nullable=True,
        comment="When schema analysis was performed"
    )

    analysis_errors = Column(
        Text,
        nullable=True,
        comment="Any errors encountered during analysis"
    )

    # Relationships
    excel_file = relationship(
        "ExcelFile",
        back_populates="excel_sheets"
    )

    column_definitions = relationship(
        "ColumnDefinition",
        back_populates="excel_sheet",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "sheet_index >= 0",
            name="valid_sheet_index"
        ),
        CheckConstraint(
            "row_count IS NULL OR row_count >= 0",
            name="valid_row_count"
        ),
        CheckConstraint(
            "column_count IS NULL OR column_count >= 0",
            name="valid_column_count"
        ),
        CheckConstraint(
            "header_row >= 0",
            name="valid_header_row"
        ),
        CheckConstraint(
            "data_start_row >= 0",
            name="valid_data_start_row"
        ),
        CheckConstraint(
            "empty_rows IS NULL OR empty_rows >= 0",
            name="valid_empty_rows"
        ),
        CheckConstraint(
            "empty_columns IS NULL OR empty_columns >= 0",
            name="valid_empty_columns"
        ),
        CheckConstraint(
            "oews_sheet_type IS NULL OR oews_sheet_type IN ('data', 'field_descriptions', 'update_time', 'filler')",
            name="valid_oews_sheet_type"
        )
    )

    @validates('sheet_name')
    def validate_sheet_name(self, key: str, sheet_name: str) -> str:
        """Validate that sheet_name is not empty"""
        if not sheet_name or not sheet_name.strip():
            raise ValueError("sheet_name cannot be empty")
        return sheet_name.strip()

    @validates('inferred_schema')
    def validate_inferred_schema(self, key: str, schema: Any) -> Optional[Dict]:
        """Validate that inferred_schema is valid JSON"""
        if schema is None:
            return None

        if isinstance(schema, str):
            try:
                schema = json.loads(schema)
            except json.JSONDecodeError:
                raise ValueError("inferred_schema must be valid JSON")

        if not isinstance(schema, dict):
            raise ValueError("inferred_schema must be a JSON object")

        return schema

    @validates('data_density')
    def validate_data_density(self, key: str, density: Optional[str]) -> Optional[str]:
        """Validate data density percentage format"""
        if density is None:
            return None

        if not isinstance(density, str) or not density.endswith('%'):
            raise ValueError("data_density must be a percentage string like '85.3%'")

        try:
            percentage = float(density[:-1])
            if not 0 <= percentage <= 100:
                raise ValueError("data_density percentage must be between 0 and 100")
        except ValueError:
            raise ValueError("data_density must be a valid percentage string")

        return density

    def is_oews_data_sheet(self) -> bool:
        """Check if this is the main OEWS data sheet"""
        if self.oews_sheet_type == 'data':
            return True

        # Fallback: check sheet name patterns
        data_patterns = [
            'all may',
            'data',
            'employment',
            'wages'
        ]

        sheet_name_lower = self.sheet_name.lower()
        return any(pattern in sheet_name_lower for pattern in data_patterns)

    def is_oews_metadata_sheet(self) -> bool:
        """Check if this is an OEWS metadata sheet"""
        if self.oews_sheet_type in ['field_descriptions', 'update_time', 'filler']:
            return True

        # Fallback: check sheet name patterns
        metadata_patterns = [
            'field descriptions',
            'updatetime',
            'update time',
            'filler'
        ]

        sheet_name_lower = self.sheet_name.lower()
        return any(pattern in sheet_name_lower for pattern in metadata_patterns)

    def get_schema_dict(self) -> Dict[str, Any]:
        """Get inferred schema as dictionary"""
        if self.inferred_schema is None:
            return {}

        if isinstance(self.inferred_schema, str):
            try:
                return json.loads(self.inferred_schema)
            except json.JSONDecodeError:
                return {}

        return self.inferred_schema or {}

    def set_schema_dict(self, schema: Dict[str, Any]) -> None:
        """Set inferred schema from dictionary"""
        self.inferred_schema = schema

    def get_column_names(self) -> List[str]:
        """Get list of column names from schema"""
        schema = self.get_schema_dict()
        columns = schema.get('columns', [])

        if isinstance(columns, list):
            return [col.get('name', '') for col in columns if isinstance(col, dict)]
        elif isinstance(columns, dict):
            return list(columns.keys())
        else:
            return []

    def get_data_rows_count(self) -> int:
        """Get number of actual data rows (excluding headers)"""
        if self.row_count is None:
            return 0

        data_rows = self.row_count - self.data_start_row
        return max(0, data_rows)

    def calculate_data_density(self) -> Optional[str]:
        """
        Calculate data density percentage based on row/column counts

        Returns:
            Data density as percentage string or None if insufficient data
        """
        if not all([self.row_count, self.column_count]):
            return None

        total_cells = self.row_count * self.column_count
        if total_cells == 0:
            return "0.0%"

        # Estimate non-empty cells (simple heuristic)
        empty_cell_estimate = (
            (self.empty_rows or 0) * self.column_count +
            (self.empty_columns or 0) * self.row_count
        )

        non_empty_cells = max(0, total_cells - empty_cell_estimate)
        density = (non_empty_cells / total_cells) * 100

        return f"{density:.1f}%"

    def is_analysis_stale(self, hours: int = 24) -> bool:
        """
        Check if schema analysis is stale

        Args:
            hours: Number of hours after which analysis is considered stale

        Returns:
            True if analysis should be refreshed
        """
        if not self.analyzed_at:
            return True

        try:
            from datetime import datetime, timedelta
            analyzed_time = datetime.fromisoformat(self.analyzed_at.replace('Z', '+00:00'))
            return datetime.utcnow() - analyzed_time > timedelta(hours=hours)
        except (ValueError, TypeError):
            return True

    def get_expected_oews_columns(self) -> List[str]:
        """Get list of expected OEWS columns for data validation"""
        if not self.is_oews_data_sheet():
            return []

        # Standard OEWS columns (32 total as per real data analysis)
        return [
            'AREA', 'AREA_TITLE', 'AREA_TYPE', 'PRIM_STATE', 'NAICS', 'NAICS_TITLE',
            'I_GROUP', 'OWN_CODE', 'OCC_CODE', 'OCC_TITLE', 'O_GROUP', 'TOT_EMP',
            'EMP_PRSE', 'JOBS_1000', 'LOC_QUOTIENT', 'PCT_TOTAL', 'PCT_RPT', 'H_MEAN',
            'A_MEAN', 'MEAN_PRSE', 'H_PCT10', 'H_PCT25', 'H_MEDIAN', 'H_PCT75',
            'H_PCT90', 'A_PCT10', 'A_PCT25', 'A_MEDIAN', 'A_PCT75', 'A_PCT90',
            'ANNUAL', 'HOURLY'
        ]

    def validate_oews_structure(self) -> List[str]:
        """
        Validate sheet structure against expected OEWS format

        Returns:
            List of validation issues (empty if no issues)
        """
        issues = []

        if not self.is_oews_data_sheet():
            return issues  # Only validate data sheets

        expected_columns = self.get_expected_oews_columns()
        actual_columns = self.get_column_names()

        # Check for missing critical columns
        missing_columns = set(expected_columns) - set(actual_columns)
        if missing_columns:
            issues.append(f"Missing expected OEWS columns: {sorted(missing_columns)}")

        # Check for unexpected extra columns
        extra_columns = set(actual_columns) - set(expected_columns)
        if extra_columns:
            issues.append(f"Unexpected columns found: {sorted(extra_columns)}")

        # Check column count
        if len(actual_columns) != 32:
            issues.append(f"Expected 32 columns but found {len(actual_columns)}")

        return issues

    def __repr__(self) -> str:
        """String representation of the ExcelSheet"""
        return f"<ExcelSheet(sheet_name='{self.sheet_name}', rows={self.row_count}, cols={self.column_count})>"