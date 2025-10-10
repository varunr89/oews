"""
Excel Schema Analyzer Service

Analyzes Excel file structures to infer schema definitions.
Maps to FR-002: System MUST analyze Excel file structures to identify column names,
data types, and relationships across multiple files.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
import pandas as pd

from src.lib.excel_parser import ExcelParser
from src.lib.type_converter import TypeConverter

logger = logging.getLogger(__name__)


@dataclass
class ColumnSchema:
    """Schema information for a single column"""
    name: str
    sql_type: Any  # SQLAlchemy type
    nullable: bool
    sample_values: List[Any]
    special_values_count: int
    unique_values_count: int
    data_pattern: Optional[str] = None  # e.g., "numeric", "text", "date"


@dataclass
class SheetSchema:
    """Schema information for a single sheet"""
    sheet_name: str
    columns: List[ColumnSchema]
    total_rows: int
    header_row: int


@dataclass
class FileSchema:
    """Complete schema information for an Excel file"""
    file_path: Path
    file_name: str
    sheets: List[SheetSchema]
    total_sheets: int


class SchemaAnalyzer:
    """
    Excel schema analyzer service

    Analyzes Excel files to infer structure, data types, and patterns.
    Provides schema information for unified database schema creation.
    """

    def __init__(self):
        """Initialize schema analyzer with parser and type converter"""
        self.excel_parser = ExcelParser()
        self.type_converter = TypeConverter()
        self.logger = logging.getLogger(__name__)

    def analyze_file(self, file_path: Path, sample_size: int = 1000) -> FileSchema:
        """
        Analyze an Excel file to infer its schema

        Args:
            file_path: Path to the Excel file
            sample_size: Number of rows to sample for type inference

        Returns:
            FileSchema containing structure information

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be analyzed
        """
        self.logger.info(f"Analyzing schema for file: {file_path.name}")

        try:
            # Get all sheets
            sheets_dict = self.excel_parser.parse_file(file_path)

            # Analyze each sheet
            sheet_schemas: List[SheetSchema] = []

            for sheet_name, df in sheets_dict.items():
                self.logger.debug(f"Analyzing sheet: {sheet_name}")

                sheet_schema = self._analyze_sheet(sheet_name, df, sample_size)
                sheet_schemas.append(sheet_schema)

            file_schema = FileSchema(
                file_path=file_path,
                file_name=file_path.name,
                sheets=sheet_schemas,
                total_sheets=len(sheet_schemas)
            )

            self.logger.info(
                f"Schema analysis complete: {len(sheet_schemas)} sheets, "
                f"{sum(len(s.columns) for s in sheet_schemas)} total columns"
            )

            return file_schema

        except FileNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to analyze file {file_path}: {str(e)}")
            raise ValueError(f"Cannot analyze file schema: {str(e)}")

    def _analyze_sheet(
        self,
        sheet_name: str,
        dataframe: pd.DataFrame,
        sample_size: int
    ) -> SheetSchema:
        """
        Analyze a single sheet to infer its schema

        Args:
            sheet_name: Name of the sheet
            dataframe: DataFrame containing sheet data
            sample_size: Number of rows to sample

        Returns:
            SheetSchema containing column information
        """
        columns: List[ColumnSchema] = []

        # Analyze each column
        for column_name in dataframe.columns:
            column_schema = self._analyze_column(
                column_name,
                dataframe[column_name],
                sample_size
            )
            columns.append(column_schema)

        return SheetSchema(
            sheet_name=sheet_name,
            columns=columns,
            total_rows=len(dataframe),
            header_row=0  # Assuming first row is header
        )

    def _analyze_column(
        self,
        column_name: str,
        column_data: pd.Series,
        sample_size: int
    ) -> ColumnSchema:
        """
        Analyze a single column to infer its schema

        Args:
            column_name: Name of the column
            column_data: Series containing column data
            sample_size: Number of values to sample

        Returns:
            ColumnSchema with type and pattern information
        """
        # Get sample values (non-null)
        sample_values = column_data.dropna().head(sample_size).tolist()

        # Infer SQL type
        sql_type = self.type_converter.infer_column_type(
            pd.DataFrame({column_name: column_data}),
            column_name,
            sample_size
        )

        # Calculate statistics
        total_values = len(column_data)
        null_count = column_data.isna().sum()
        nullable = null_count > 0

        # Count special OEWS values
        special_values_count = sum(
            1 for v in column_data
            if self.excel_parser.is_oews_special_value(v)
        )

        # Count unique values (excluding nulls)
        unique_values_count = column_data.dropna().nunique()

        # Determine data pattern
        data_pattern = self._infer_data_pattern(column_data, sql_type)

        return ColumnSchema(
            name=str(column_name),
            sql_type=sql_type,
            nullable=nullable,
            sample_values=sample_values[:10],  # Keep only 10 samples
            special_values_count=special_values_count,
            unique_values_count=unique_values_count,
            data_pattern=data_pattern
        )

    def _infer_data_pattern(self, column_data: pd.Series, sql_type: Any) -> str:
        """
        Infer the data pattern of a column

        Args:
            column_data: Column data
            sql_type: Inferred SQL type

        Returns:
            Pattern description (e.g., "numeric", "text", "date")
        """
        if self.type_converter.is_numeric_type(sql_type):
            return "numeric"
        elif self.type_converter.is_string_type(sql_type):
            # Check if it looks like a code or identifier
            sample_values = column_data.dropna().head(100).astype(str)
            if sample_values.str.match(r'^[A-Z0-9-]+$').sum() > len(sample_values) * 0.8:
                return "code"
            return "text"
        elif 'DateTime' in str(type(sql_type)):
            return "datetime"
        elif 'Date' in str(type(sql_type)):
            return "date"
        elif 'Boolean' in str(type(sql_type)):
            return "boolean"
        else:
            return "unknown"

    def analyze_multiple_files(
        self,
        file_paths: List[Path],
        sample_size: int = 1000
    ) -> List[FileSchema]:
        """
        Analyze multiple Excel files

        Args:
            file_paths: List of file paths to analyze
            sample_size: Number of rows to sample per file

        Returns:
            List of FileSchema objects
        """
        schemas: List[FileSchema] = []

        for file_path in file_paths:
            try:
                schema = self.analyze_file(file_path, sample_size)
                schemas.append(schema)
            except Exception as e:
                self.logger.error(f"Failed to analyze {file_path}: {str(e)}")

        self.logger.info(f"Analyzed {len(schemas)} files successfully")
        return schemas

    def find_common_columns(self, file_schemas: List[FileSchema]) -> Dict[str, Set[str]]:
        """
        Find columns that appear across multiple files

        Args:
            file_schemas: List of file schemas to compare

        Returns:
            Dictionary mapping column names to set of files containing them
        """
        column_occurrences: Dict[str, Set[str]] = {}

        for file_schema in file_schemas:
            for sheet_schema in file_schema.sheets:
                for column_schema in sheet_schema.columns:
                    column_name = column_schema.name

                    if column_name not in column_occurrences:
                        column_occurrences[column_name] = set()

                    column_occurrences[column_name].add(file_schema.file_name)

        self.logger.debug(f"Found {len(column_occurrences)} unique columns across files")
        return column_occurrences

    def detect_schema_evolution(
        self,
        file_schemas: List[FileSchema]
    ) -> Dict[str, List[Any]]:
        """
        Detect schema changes across files (for different years of OEWS data)

        Args:
            file_schemas: List of file schemas to compare

        Returns:
            Dictionary mapping column names to list of different SQL types found
        """
        column_types: Dict[str, List[Any]] = {}

        for file_schema in file_schemas:
            for sheet_schema in file_schema.sheets:
                for column_schema in sheet_schema.columns:
                    column_name = column_schema.name

                    if column_name not in column_types:
                        column_types[column_name] = []

                    # Add type if not already in list
                    type_str = str(column_schema.sql_type)
                    if type_str not in [str(t) for t in column_types[column_name]]:
                        column_types[column_name].append(column_schema.sql_type)

        # Filter to only columns with multiple types (schema evolution)
        evolved_columns = {
            k: v for k, v in column_types.items() if len(v) > 1
        }

        if evolved_columns:
            self.logger.warning(
                f"Detected schema evolution in {len(evolved_columns)} columns"
            )

        return evolved_columns

    def get_unified_column_list(
        self,
        file_schemas: List[FileSchema]
    ) -> List[Dict[str, Any]]:
        """
        Get a unified list of all columns across all files

        Args:
            file_schemas: List of file schemas

        Returns:
            List of dictionaries with column information
        """
        all_columns: Dict[str, Dict[str, Any]] = {}

        for file_schema in file_schemas:
            for sheet_schema in file_schema.sheets:
                for column_schema in sheet_schema.columns:
                    column_name = column_schema.name

                    if column_name not in all_columns:
                        all_columns[column_name] = {
                            'name': column_name,
                            'sql_type': column_schema.sql_type,
                            'nullable': column_schema.nullable,
                            'data_pattern': column_schema.data_pattern,
                            'source_files': []
                        }

                    all_columns[column_name]['source_files'].append(file_schema.file_name)

        unified_columns = list(all_columns.values())
        self.logger.info(f"Created unified column list with {len(unified_columns)} columns")

        return unified_columns
