"""Schema metadata for OEWS database."""

from typing import List, Dict, Any

# Table list
TABLES = ['oews_data', 'data_vintages']

# Schema descriptions for LLM context
OEWS_DATA_SCHEMA = """
Table: oews_data

Description: Occupational Employment and Wage Statistics (OEWS) data from the U.S. Bureau of Labor Statistics.
Contains employment and wage data by occupation, geographic area, and industry.

Key Columns:
- AREA_TITLE (TEXT): Geographic location name (e.g., "Bellingham, WA", "California", "United States")
- AREA_TYPE (INTEGER): Geographic level (1=National, 2=State, 4=Metropolitan/Micropolitan area)
- PRIM_STATE (TEXT): Primary state code (e.g., "WA", "CA")

- OCC_TITLE (TEXT): Occupation name (e.g., "Software Developers", "Registered Nurses")
- OCC_CODE (TEXT): SOC (Standard Occupational Classification) code
- O_GROUP (TEXT): Occupation group level (total, major, minor, broad, detailed)

- TOT_EMP (INTEGER): Total employment count for this occupation/area
- JOBS_1000 (REAL): Jobs per 1,000 total employment in the area
- LOC_QUOTIENT (REAL): Location quotient (concentration vs. national average)

- A_MEAN (REAL): Mean annual wage
- A_MEDIAN (REAL): Median annual wage (more robust than mean)
- A_PCT10, A_PCT25, A_PCT75, A_PCT90 (REAL): Annual wage percentiles

- H_MEAN (REAL): Mean hourly wage
- H_MEDIAN (REAL): Median hourly wage
- H_PCT10, H_PCT25, H_PCT75, H_PCT90 (REAL): Hourly wage percentiles

- NAICS (TEXT): Industry code (North American Industry Classification System)
- NAICS_TITLE (TEXT): Industry name

- SURVEY_YEAR (INTEGER): Year of the survey data
- SURVEY_MONTH (TEXT): Month of the survey (typically "May")

Common Query Patterns:
1. Filter by location:
   WHERE AREA_TITLE LIKE ?  -- Use parameterized queries!
   WHERE AREA_TYPE = ?

2. Filter by occupation:
   WHERE OCC_TITLE LIKE ?
   WHERE OCC_CODE LIKE ?

3. Salary comparisons (use A_MEDIAN, not A_MEAN):
   SELECT AREA_TITLE, OCC_TITLE, A_MEDIAN
   ORDER BY A_MEDIAN DESC

4. Employment analysis:
   SELECT OCC_TITLE, SUM(TOT_EMP) as total_jobs
   GROUP BY OCC_TITLE
   ORDER BY total_jobs DESC

SECURITY REQUIREMENTS:
- ALL user inputs MUST use parameterized queries with ? placeholders
- NEVER use f-strings or .format() to insert user data into SQL
- Use wildcards (%) as part of the parameter value, not in the query string
"""

DATA_VINTAGES_SCHEMA = """
Table: data_vintages

Description: Metadata about data import timestamps and source files.

Columns:
- SOURCE_FILE (TEXT): Original filename
- SOURCE_FOLDER (TEXT): Source directory
- IMPORTED_AT (TEXT): Timestamp of import
"""


def get_table_list() -> List[str]:
    """
    Get list of available tables in the OEWS database.

    Returns:
        List of table names
    """
    return TABLES.copy()


def get_oews_schema_description(table_name: str) -> str:
    """
    Get detailed schema description for a table.

    This description is optimized for LLM context to help with
    SQL query generation.

    Args:
        table_name: Name of the table

    Returns:
        Detailed schema description string

    Raises:
        ValueError: If table name is not recognized
    """
    schemas = {
        'oews_data': OEWS_DATA_SCHEMA,
        'data_vintages': DATA_VINTAGES_SCHEMA
    }

    if table_name not in schemas:
        raise ValueError(f"Unknown table: {table_name}. Available: {list(schemas.keys())}")

    return schemas[table_name].strip()


def get_all_schemas() -> str:
    """
    Get schema descriptions for all tables.

    Returns:
        Combined schema descriptions
    """
    return "\n\n".join([
        get_oews_schema_description(table)
        for table in TABLES
    ])
