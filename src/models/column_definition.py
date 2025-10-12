"""
ColumnDefinition Model

Defines individual columns within Excel sheets and their mapping to database schema.
Maps to schema analysis and type inference requirements.
"""

import json
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import Column, String, Integer, Boolean, Float, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID, JSON

from . import Base, ExcelDataType, SQLDataType


class ColumnDefinition(Base):
    """
    Defines individual columns within Excel sheets and their mapping to database schema

    This model captures detailed column metadata including type inference,
    statistics, and mapping information for data migration.
    """

    # Parent relationship
    excel_sheet_id = Column(
        UUID(as_uuid=True),
        ForeignKey('excel_sheet.id', ondelete='CASCADE'),
        nullable=False,
        comment="Foreign key to ExcelSheet"
    )

    # Column identification
    column_name = Column(
        String(255),
        nullable=False,
        comment="Original column name from Excel"
    )

    column_index = Column(
        Integer,
        nullable=False,
        comment="Zero-based column position"
    )

    normalized_name = Column(
        String(255),
        nullable=True,
        comment="Standardized column name for database"
    )

    # Data type information
    excel_data_type = Column(
        String(20),
        nullable=True,
        comment="Excel data type classification"
    )

    sql_data_type = Column(
        String(20),
        nullable=True,
        comment="Target SQL data type"
    )

    # Size and constraints
    max_length = Column(
        Integer,
        nullable=True,
        comment="Maximum observed string length for VARCHAR sizing"
    )

    precision = Column(
        Integer,
        nullable=True,
        comment="Decimal precision for numeric types"
    )

    scale = Column(
        Integer,
        nullable=True,
        comment="Decimal scale for numeric types"
    )

    nullable = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether column allows NULL values"
    )

    # Data characteristics
    has_duplicates = Column(
        Boolean,
        nullable=True,
        comment="Whether column contains duplicate values"
    )

    unique_count = Column(
        Integer,
        nullable=True,
        comment="Number of unique values in column"
    )

    null_count = Column(
        Integer,
        nullable=True,
        comment="Number of NULL/empty values"
    )

    # Sample data for validation
    sample_values = Column(
        JSON,
        nullable=True,
        comment="Array of sample values for validation"
    )

    # Type inference metadata
    mapping_confidence = Column(
        Float,
        nullable=True,
        comment="Confidence score for type inference (0.0-1.0)"
    )

    inference_rules_applied = Column(
        JSON,
        nullable=True,
        comment="List of type inference rules that were applied"
    )

    # OEWS-specific metadata
    is_oews_standard = Column(
        Boolean,
        nullable=True,
        comment="Whether this is a standard OEWS column"
    )

    oews_column_type = Column(
        String(50),
        nullable=True,
        comment="OEWS column classification: geographic, occupation, industry, wage, employment"
    )

    # Data quality indicators
    has_special_values = Column(
        Boolean,
        nullable=True,
        comment="Whether column contains OEWS special values like '#' or '*'"
    )

    special_values_count = Column(
        Integer,
        nullable=True,
        comment="Count of special/suppressed values"
    )

    # Validation and constraints
    validation_rules = Column(
        JSON,
        nullable=True,
        comment="Custom validation rules for this column"
    )

    validation_errors = Column(
        Text,
        nullable=True,
        comment="Any validation errors found in column data"
    )

    # Relationships
    excel_sheet = relationship(
        "ExcelSheet",
        back_populates="column_definitions"
    )

    column_mappings = relationship(
        "ColumnMapping",
        back_populates="column_definition",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "column_index >= 0",
            name="valid_column_index"
        ),
        CheckConstraint(
            "max_length IS NULL OR max_length > 0",
            name="valid_max_length"
        ),
        CheckConstraint(
            "precision IS NULL OR precision > 0",
            name="valid_precision"
        ),
        CheckConstraint(
            "scale IS NULL OR scale >= 0",
            name="valid_scale"
        ),
        CheckConstraint(
            "unique_count IS NULL OR unique_count >= 0",
            name="valid_unique_count"
        ),
        CheckConstraint(
            "null_count IS NULL OR null_count >= 0",
            name="valid_null_count"
        ),
        CheckConstraint(
            "mapping_confidence IS NULL OR (mapping_confidence >= 0.0 AND mapping_confidence <= 1.0)",
            name="valid_mapping_confidence"
        ),
        CheckConstraint(
            "special_values_count IS NULL OR special_values_count >= 0",
            name="valid_special_values_count"
        ),
        CheckConstraint(
            "excel_data_type IS NULL OR excel_data_type IN ('text', 'numeric', 'date', 'boolean', 'formula')",
            name="valid_excel_data_type"
        ),
        CheckConstraint(
            "sql_data_type IS NULL OR sql_data_type IN ('varchar', 'text', 'integer', 'bigint', 'decimal', 'float', 'date', 'datetime', 'timestamp', 'boolean', 'json')",
            name="valid_sql_data_type"
        ),
        CheckConstraint(
            "oews_column_type IS NULL OR oews_column_type IN ('geographic', 'occupation', 'industry', 'wage', 'employment', 'metadata', 'other')",
            name="valid_oews_column_type"
        )
    )

    @validates('column_name')
    def validate_column_name(self, key: str, column_name: str) -> str:
        """Validate that column_name is not empty"""
        if not column_name or not column_name.strip():
            raise ValueError("column_name cannot be empty")
        return column_name.strip()

    @validates('excel_data_type')
    def validate_excel_data_type(self, key: str, data_type: Optional[str]) -> Optional[str]:
        """Validate Excel data type"""
        if data_type is None:
            return None

        valid_types = [
            ExcelDataType.TEXT,
            ExcelDataType.NUMERIC,
            ExcelDataType.DATE,
            ExcelDataType.BOOLEAN,
            ExcelDataType.FORMULA
        ]

        if data_type not in valid_types:
            raise ValueError(f"Invalid excel_data_type: {data_type}. Must be one of {valid_types}")

        return data_type

    @validates('sql_data_type')
    def validate_sql_data_type(self, key: str, data_type: Optional[str]) -> Optional[str]:
        """Validate SQL data type"""
        if data_type is None:
            return None

        valid_types = [
            SQLDataType.VARCHAR, SQLDataType.TEXT, SQLDataType.INTEGER,
            SQLDataType.BIGINT, SQLDataType.DECIMAL, SQLDataType.FLOAT,
            SQLDataType.DATE, SQLDataType.DATETIME, SQLDataType.TIMESTAMP,
            SQLDataType.BOOLEAN, SQLDataType.JSON
        ]

        if data_type not in valid_types:
            raise ValueError(f"Invalid sql_data_type: {data_type}. Must be one of {valid_types}")

        return data_type

    @validates('sample_values')
    def validate_sample_values(self, key: str, values: Any) -> Optional[List]:
        """Validate sample values format"""
        if values is None:
            return None

        if isinstance(values, str):
            try:
                values = json.loads(values)
            except json.JSONDecodeError:
                raise ValueError("sample_values must be valid JSON array")

        if not isinstance(values, list):
            raise ValueError("sample_values must be a JSON array")

        # Limit sample size to prevent bloat
        if len(values) > 100:
            values = values[:100]

        return values

    def normalize_column_name(self) -> str:
        """
        Generate normalized column name for database use

        Returns:
            Normalized column name suitable for database
        """
        if self.normalized_name:
            return self.normalized_name

        # Basic normalization: lowercase, replace spaces/special chars with underscores
        import re
        normalized = re.sub(r'[^\w\s]', '', self.column_name)  # Remove special chars
        normalized = re.sub(r'\s+', '_', normalized)  # Replace spaces with underscores
        normalized = normalized.lower().strip('_')  # Lowercase and trim underscores

        # Handle empty result
        if not normalized:
            normalized = f"column_{self.column_index}"

        # Ensure it doesn't start with a number
        if normalized and normalized[0].isdigit():
            normalized = f"col_{normalized}"

        return normalized

    def infer_sql_type(self) -> str:
        """
        Infer appropriate SQL data type based on Excel type and characteristics

        Returns:
            Recommended SQL data type
        """
        if self.sql_data_type:
            return self.sql_data_type

        # Map Excel types to SQL types
        type_mapping = {
            ExcelDataType.TEXT: SQLDataType.VARCHAR,
            ExcelDataType.NUMERIC: SQLDataType.DECIMAL,
            ExcelDataType.DATE: SQLDataType.DATE,
            ExcelDataType.BOOLEAN: SQLDataType.BOOLEAN,
            ExcelDataType.FORMULA: SQLDataType.TEXT
        }

        base_type = type_mapping.get(self.excel_data_type, SQLDataType.TEXT)

        # Refine based on characteristics
        if base_type == SQLDataType.VARCHAR and self.max_length:
            if self.max_length > 255:
                return SQLDataType.TEXT
            else:
                return SQLDataType.VARCHAR

        if base_type == SQLDataType.DECIMAL:
            # Use INTEGER for whole numbers without decimals
            if self.scale == 0 or not self.has_decimal_values():
                if self.max_length and self.max_length <= 10:
                    return SQLDataType.INTEGER
                else:
                    return SQLDataType.BIGINT

        return base_type

    def has_decimal_values(self) -> bool:
        """Check if numeric column contains decimal values"""
        if not self.sample_values:
            return False

        try:
            for value in self.sample_values:
                if value is not None and isinstance(value, (int, float, str)):
                    if isinstance(value, float) and value != int(value):
                        return True
                    if isinstance(value, str) and '.' in value:
                        try:
                            float_val = float(value)
                            if float_val != int(float_val):
                                return True
                        except ValueError:
                            continue
        except (TypeError, AttributeError):
            pass

        return False

    def is_oews_standard_column(self) -> bool:
        """Check if this is a standard OEWS column"""
        if self.is_oews_standard is not None:
            return self.is_oews_standard

        # Check against known OEWS column names
        standard_oews_columns = {
            'AREA', 'AREA_TITLE', 'AREA_TYPE', 'PRIM_STATE', 'NAICS', 'NAICS_TITLE',
            'I_GROUP', 'OWN_CODE', 'OCC_CODE', 'OCC_TITLE', 'O_GROUP', 'TOT_EMP',
            'EMP_PRSE', 'JOBS_1000', 'LOC_QUOTIENT', 'PCT_TOTAL', 'PCT_RPT', 'H_MEAN',
            'A_MEAN', 'MEAN_PRSE', 'H_PCT10', 'H_PCT25', 'H_MEDIAN', 'H_PCT75',
            'H_PCT90', 'A_PCT10', 'A_PCT25', 'A_MEDIAN', 'A_PCT75', 'A_PCT90',
            'ANNUAL', 'HOURLY'
        }

        return self.column_name.upper() in standard_oews_columns

    def classify_oews_column_type(self) -> str:
        """
        Classify column into OEWS data categories

        Returns:
            OEWS column type classification
        """
        if self.oews_column_type:
            return self.oews_column_type

        column_name = self.column_name.upper()

        # Geographic columns
        if any(geo in column_name for geo in ['AREA', 'STATE', 'MSA', 'COUNTY']):
            return 'geographic'

        # Occupation columns
        if any(occ in column_name for occ in ['OCC_', 'OCCUPATION']):
            return 'occupation'

        # Industry columns
        if any(ind in column_name for ind in ['NAICS', 'INDUSTRY', 'I_GROUP']):
            return 'industry'

        # Wage columns
        if any(wage in column_name for wage in ['WAGE', 'H_', 'A_', 'MEAN', 'PCT', 'ANNUAL', 'HOURLY']):
            return 'wage'

        # Employment columns
        if any(emp in column_name for emp in ['EMP', 'EMPLOYMENT', 'TOT_', 'JOBS']):
            return 'employment'

        # Metadata columns
        if any(meta in column_name for meta in ['PRSE', 'RPT', 'GROUP', 'CODE', 'TITLE']):
            return 'metadata'

        return 'other'

    def get_sample_values_list(self) -> List[Any]:
        """Get sample values as a list"""
        if not self.sample_values:
            return []

        if isinstance(self.sample_values, str):
            try:
                return json.loads(self.sample_values)
            except json.JSONDecodeError:
                return []

        return self.sample_values or []

    def add_sample_value(self, value: Any) -> None:
        """Add a sample value to the collection"""
        current_samples = self.get_sample_values_list()

        # Add if not already present and under limit
        if value not in current_samples and len(current_samples) < 100:
            current_samples.append(value)
            self.sample_values = current_samples

    def calculate_data_quality_score(self) -> float:
        """
        Calculate data quality score based on various factors

        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 1.0

        # Penalize high null count
        if self.null_count and self.excel_sheet and self.excel_sheet.row_count:
            null_ratio = self.null_count / self.excel_sheet.row_count
            score -= null_ratio * 0.3

        # Penalize low mapping confidence
        if self.mapping_confidence is not None:
            score *= self.mapping_confidence

        # Penalize high special values count
        if self.special_values_count and self.excel_sheet and self.excel_sheet.row_count:
            special_ratio = self.special_values_count / self.excel_sheet.row_count
            score -= special_ratio * 0.2

        # Bonus for being standard OEWS column
        if self.is_oews_standard_column():
            score = min(1.0, score + 0.1)

        return max(0.0, score)

    def __repr__(self) -> str:
        """String representation of the ColumnDefinition"""
        return f"<ColumnDefinition(column_name='{self.column_name}', type='{self.excel_data_type}→{self.sql_data_type}')>"