"""
Data Type Conversion Utilities

Provides utilities for converting Excel data types to SQL database types.
Handles OEWS-specific data patterns and type inference.
"""

import logging
from typing import Any, Optional, Union, List
from datetime import datetime, date
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Date, Text, Numeric
)

logger = logging.getLogger(__name__)


class TypeConverter:
    """
    Data type conversion utilities for Excel to SQL migration

    Handles type inference, conversion, and mapping between Excel data
    and SQL database types with support for OEWS-specific patterns.
    """

    # OEWS special value markers
    SPECIAL_VALUES = {'#', '*', 'N/A', 'n/a', 'NA'}

    # SQL type mapping based on inferred Python/pandas types
    TYPE_MAP = {
        'int64': Integer,
        'int32': Integer,
        'float64': Float,
        'float32': Float,
        'object': String(255),
        'bool': Boolean,
        'datetime64[ns]': DateTime,
        'category': String(255),
        'string': String(255),
    }

    def __init__(self):
        """Initialize the type converter"""
        self.type_cache = {}

    def infer_sql_type(
        self,
        pandas_dtype: Any,
        sample_values: Optional[List[Any]] = None,
        max_length: int = 255
    ) -> sa.types.TypeEngine:
        """
        Infer SQL type from pandas dtype and sample values

        Args:
            pandas_dtype: Pandas dtype of the column
            sample_values: Sample values for better type inference
            max_length: Maximum length for string types

        Returns:
            SQLAlchemy type object
        """
        dtype_str = str(pandas_dtype)

        # Check cache first
        cache_key = f"{dtype_str}_{max_length}"
        if cache_key in self.type_cache:
            return self.type_cache[cache_key]

        # Handle special cases with sample values
        if sample_values:
            sql_type = self._infer_from_samples(sample_values, max_length)
            if sql_type:
                self.type_cache[cache_key] = sql_type
                return sql_type

        # Map pandas dtype to SQL type
        if dtype_str in self.TYPE_MAP:
            sql_type = self.TYPE_MAP[dtype_str]
        elif 'int' in dtype_str:
            sql_type = Integer
        elif 'float' in dtype_str:
            sql_type = Float
        elif 'datetime' in dtype_str:
            sql_type = DateTime
        elif 'bool' in dtype_str:
            sql_type = Boolean
        else:
            # Default to String for unknown types
            sql_type = String(max_length)

        self.type_cache[cache_key] = sql_type
        logger.debug(f"Inferred SQL type {sql_type} for pandas dtype {dtype_str}")
        return sql_type

    def _infer_from_samples(
        self,
        sample_values: List[Any],
        max_length: int
    ) -> Optional[sa.types.TypeEngine]:
        """
        Infer SQL type from sample values

        Args:
            sample_values: Sample values to analyze
            max_length: Maximum length for string types

        Returns:
            SQLAlchemy type or None if cannot infer
        """
        # Filter out None and special values
        clean_values = [
            v for v in sample_values
            if v is not None
            and not pd.isna(v)
            and str(v).strip() not in self.SPECIAL_VALUES
        ]

        if not clean_values:
            return None

        # Check for dates
        if all(isinstance(v, (date, datetime)) for v in clean_values):
            if all(isinstance(v, datetime) for v in clean_values):
                return DateTime
            return Date

        # Check for integers
        if all(isinstance(v, (int, bool)) and not isinstance(v, bool) for v in clean_values):
            return Integer

        # Check for floats
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in clean_values):
            return Float

        # Check for booleans
        if all(isinstance(v, bool) for v in clean_values):
            return Boolean

        # Check string length for String vs Text
        if all(isinstance(v, str) for v in clean_values):
            max_str_length = max(len(str(v)) for v in clean_values)
            if max_str_length > max_length:
                return Text
            return String(max_length)

        return None

    def convert_value(
        self,
        value: Any,
        target_type: sa.types.TypeEngine,
        allow_special_values: bool = True
    ) -> Any:
        """
        Convert a value to match the target SQL type

        Args:
            value: Value to convert
            target_type: Target SQLAlchemy type
            allow_special_values: Whether to preserve OEWS special values

        Returns:
            Converted value or None if conversion fails
        """
        # Handle None and NaN
        if value is None or pd.isna(value):
            return None

        # Handle OEWS special values
        value_str = str(value).strip()
        if allow_special_values and value_str in self.SPECIAL_VALUES:
            # Store special values as-is in string columns
            if isinstance(target_type, (String, Text)):
                return value_str
            # Convert to None for numeric/date columns
            return None

        try:
            # Convert based on target type
            if isinstance(target_type, Integer):
                return int(float(value))  # Handle '1.0' -> 1
            elif isinstance(target_type, Float):
                return float(value)
            elif isinstance(target_type, Numeric):
                return float(value)
            elif isinstance(target_type, Boolean):
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ('true', '1', 'yes', 'y')
            elif isinstance(target_type, DateTime):
                if isinstance(value, datetime):
                    return value
                if isinstance(value, str):
                    return pd.to_datetime(value)
                return value
            elif isinstance(target_type, Date):
                if isinstance(value, date):
                    return value
                if isinstance(value, str):
                    return pd.to_datetime(value).date()
                return value
            elif isinstance(target_type, (String, Text)):
                return str(value)
            else:
                # Default to string conversion
                return str(value)

        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert value '{value}' to {target_type}: {str(e)}")
            return None

    def infer_column_type(
        self,
        dataframe: pd.DataFrame,
        column_name: str,
        sample_size: int = 1000
    ) -> sa.types.TypeEngine:
        """
        Infer SQL type for a DataFrame column

        Args:
            dataframe: Pandas DataFrame
            column_name: Name of the column
            sample_size: Number of sample values to analyze

        Returns:
            SQLAlchemy type object
        """
        if column_name not in dataframe.columns:
            raise ValueError(f"Column '{column_name}' not found in DataFrame")

        column = dataframe[column_name]

        # Get sample values (skip nulls)
        sample_values = column.dropna().head(sample_size).tolist()

        # Infer type
        sql_type = self.infer_sql_type(column.dtype, sample_values)

        logger.debug(f"Inferred type {sql_type} for column '{column_name}'")
        return sql_type

    def get_column_types(
        self,
        dataframe: pd.DataFrame,
        sample_size: int = 1000
    ) -> dict[str, sa.types.TypeEngine]:
        """
        Get SQL types for all columns in a DataFrame

        Args:
            dataframe: Pandas DataFrame
            sample_size: Number of sample values to analyze per column

        Returns:
            Dictionary mapping column names to SQLAlchemy types
        """
        column_types = {}

        for column_name in dataframe.columns:
            try:
                column_types[column_name] = self.infer_column_type(
                    dataframe, column_name, sample_size
                )
            except Exception as e:
                logger.error(f"Failed to infer type for column '{column_name}': {str(e)}")
                # Default to String for failed inference
                column_types[column_name] = String(255)

        logger.info(f"Inferred types for {len(column_types)} columns")
        return column_types

    def convert_dataframe_types(
        self,
        dataframe: pd.DataFrame,
        type_map: dict[str, sa.types.TypeEngine]
    ) -> pd.DataFrame:
        """
        Convert DataFrame column types based on SQL type map

        Args:
            dataframe: Input DataFrame
            type_map: Dictionary mapping column names to SQLAlchemy types

        Returns:
            DataFrame with converted types
        """
        df_converted = dataframe.copy()

        for column_name, sql_type in type_map.items():
            if column_name not in df_converted.columns:
                continue

            try:
                # Apply conversion to each value in the column
                df_converted[column_name] = df_converted[column_name].apply(
                    lambda x: self.convert_value(x, sql_type)
                )

                logger.debug(f"Converted column '{column_name}' to {sql_type}")

            except Exception as e:
                logger.error(f"Failed to convert column '{column_name}': {str(e)}")

        logger.info(f"Converted types for {len(type_map)} columns")
        return df_converted

    def get_python_type(self, sql_type: sa.types.TypeEngine) -> type:
        """
        Get Python type from SQLAlchemy type

        Args:
            sql_type: SQLAlchemy type object

        Returns:
            Corresponding Python type
        """
        if isinstance(sql_type, Integer):
            return int
        elif isinstance(sql_type, (Float, Numeric)):
            return float
        elif isinstance(sql_type, Boolean):
            return bool
        elif isinstance(sql_type, (DateTime, Date)):
            return datetime
        elif isinstance(sql_type, (String, Text)):
            return str
        else:
            return str  # Default to string

    def is_numeric_type(self, sql_type: sa.types.TypeEngine) -> bool:
        """
        Check if SQL type is numeric

        Args:
            sql_type: SQLAlchemy type object

        Returns:
            True if the type is numeric
        """
        return isinstance(sql_type, (Integer, Float, Numeric))

    def is_string_type(self, sql_type: sa.types.TypeEngine) -> bool:
        """
        Check if SQL type is string-based

        Args:
            sql_type: SQLAlchemy type object

        Returns:
            True if the type is string-based
        """
        return isinstance(sql_type, (String, Text))
