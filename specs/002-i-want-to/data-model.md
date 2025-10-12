# Data Model: OEWS Excel to SQL Database Migration

**Date**: 2025-10-02
**Feature**: OEWS Excel to SQL Database Migration Application

## Core Entities

### ExcelFile
**Purpose**: Represents an OEWS Excel file being processed for migration

**Attributes**:
- `id`: UUID - Unique identifier for the Excel file
- `file_path`: String - Absolute path to the Excel file
- `file_name`: String - Base name of the file
- `file_size`: Integer - Size in bytes
- `file_hash`: String - SHA-256 hash for change detection
- `sheet_count`: Integer - Number of worksheets in the file
- `created_at`: DateTime - File creation timestamp
- `modified_at`: DateTime - File last modification timestamp
- `processed_at`: DateTime - When migration processing began
- `status`: Enum - DISCOVERED, ANALYZING, MIGRATING, COMPLETED, FAILED, ROLLED_BACK

**Relationships**:
- One-to-many with `ExcelSheet`
- One-to-many with `MigrationRecord`

**Validation Rules**:
- `file_path` must exist and be readable
- `file_size` must be > 0 and < 100MB (actual OEWS files are 70-80MB)
- `file_hash` must be unique for change detection
- `status` transitions: DISCOVERED → ANALYZING → MIGRATING → COMPLETED/FAILED
- `sheet_count` typically 4 for OEWS files (data, descriptions, time, filler)

### ExcelSheet
**Purpose**: Represents individual worksheets within an Excel file

**Attributes**:
- `id`: UUID - Unique identifier for the sheet
- `excel_file_id`: UUID - Foreign key to ExcelFile
- `sheet_name`: String - Name of the worksheet
- `sheet_index`: Integer - Zero-based index within the workbook
- `row_count`: Integer - Total number of data rows
- `column_count`: Integer - Total number of columns
- `header_row`: Integer - Row number containing column headers (default: 0)
- `data_start_row`: Integer - First row containing actual data
- `has_header`: Boolean - Whether the sheet has column headers
- `inferred_schema`: JSON - Detected column types and relationships

**Relationships**:
- Many-to-one with `ExcelFile`
- One-to-many with `ColumnDefinition`

**Validation Rules**:
- `sheet_name` must be non-empty
- `row_count` and `column_count` must be > 0
- `header_row` and `data_start_row` must be >= 0
- `inferred_schema` must be valid JSON

### ColumnDefinition
**Purpose**: Defines individual columns within Excel sheets and their mapping to database schema

**Attributes**:
- `id`: UUID - Unique identifier for the column
- `excel_sheet_id`: UUID - Foreign key to ExcelSheet
- `column_name`: String - Original column name from Excel
- `column_index`: Integer - Zero-based column position
- `normalized_name`: String - Standardized column name for database
- `excel_data_type`: Enum - TEXT, NUMERIC, DATE, BOOLEAN, FORMULA
- `sql_data_type`: Enum - VARCHAR, INTEGER, DECIMAL, DATE, DATETIME, BOOLEAN
- `max_length`: Integer - Maximum observed string length (for VARCHAR sizing)
- `nullable`: Boolean - Whether column allows NULL values
- `has_duplicates`: Boolean - Whether column contains duplicate values
- `sample_values`: JSON - Array of sample values for validation
- `mapping_confidence`: Float - Confidence score for type inference (0.0-1.0)

**Relationships**:
- Many-to-one with `ExcelSheet`
- One-to-many with `DataMapping`

**Validation Rules**:
- `column_name` and `normalized_name` must be non-empty
- `column_index` must be >= 0
- `mapping_confidence` must be between 0.0 and 1.0
- `max_length` required when `sql_data_type` is VARCHAR

### UnifiedSchema
**Purpose**: Represents the consolidated database schema accommodating all Excel files

**Attributes**:
- `id`: UUID - Unique identifier for the schema version
- `schema_name`: String - Name of the database schema
- `version`: String - Semantic version of the schema
- `table_definitions`: JSON - Complete table structure definitions
- `created_at`: DateTime - Schema creation timestamp
- `is_active`: Boolean - Whether this is the current active schema
- `migration_count`: Integer - Number of files migrated using this schema

**Relationships**:
- One-to-many with `TableDefinition`
- One-to-many with `MigrationBatch`

**Validation Rules**:
- `schema_name` must be valid SQL identifier
- `version` must follow semantic versioning format
- Only one schema can be `is_active` at a time
- `table_definitions` must be valid JSON schema

### TableDefinition
**Purpose**: Defines individual tables within the unified database schema

**Attributes**:
- `id`: UUID - Unique identifier for the table
- `unified_schema_id`: UUID - Foreign key to UnifiedSchema
- `table_name`: String - Name of the database table
- `primary_key_columns`: JSON - Array of primary key column names
- `foreign_key_constraints`: JSON - Foreign key relationship definitions
- `indexes`: JSON - Index definitions for performance optimization
- `partition_strategy`: Enum - NONE, BY_DATE, BY_HASH, BY_RANGE
- `estimated_row_count`: Integer - Projected number of rows

**Relationships**:
- Many-to-one with `UnifiedSchema`
- One-to-many with `ColumnMapping`

**Validation Rules**:
- `table_name` must be valid SQL identifier
- `primary_key_columns` must reference valid columns
- `estimated_row_count` must be >= 0

### ColumnMapping
**Purpose**: Maps Excel columns to unified database table columns

**Attributes**:
- `id`: UUID - Unique identifier for the mapping
- `table_definition_id`: UUID - Foreign key to TableDefinition
- `source_column_id`: UUID - Foreign key to ColumnDefinition
- `target_column_name`: String - Column name in unified table
- `transformation_rule`: String - Data transformation logic (if any)
- `validation_rule`: String - Data validation expression
- `is_required`: Boolean - Whether column is mandatory
- `default_value`: String - Default value for missing data

**Relationships**:
- Many-to-one with `TableDefinition`
- Many-to-one with `ColumnDefinition`

**Validation Rules**:
- `target_column_name` must be valid SQL identifier
- `transformation_rule` must be valid Python expression
- `validation_rule` must be valid Python boolean expression

### MigrationBatch
**Purpose**: Groups related migration operations for tracking and rollback

**Attributes**:
- `id`: UUID - Unique identifier for the batch
- `unified_schema_id`: UUID - Foreign key to UnifiedSchema
- `batch_name`: String - Descriptive name for the migration batch
- `started_at`: DateTime - Migration start timestamp
- `completed_at`: DateTime - Migration completion timestamp
- `status`: Enum - PENDING, RUNNING, COMPLETED, FAILED, ROLLED_BACK
- `total_files`: Integer - Number of files in the batch
- `processed_files`: Integer - Number of successfully processed files
- `failed_files`: Integer - Number of failed files
- `total_records`: Integer - Total records migrated
- `error_summary`: JSON - Summary of errors encountered

**Relationships**:
- Many-to-one with `UnifiedSchema`
- One-to-many with `MigrationRecord`

**Validation Rules**:
- `batch_name` must be non-empty
- `processed_files` + `failed_files` <= `total_files`
- `status` transitions: PENDING → RUNNING → COMPLETED/FAILED
- `completed_at` must be >= `started_at`

### MigrationRecord
**Purpose**: Tracks individual file migration operations within a batch

**Attributes**:
- `id`: UUID - Unique identifier for the migration record
- `migration_batch_id`: UUID - Foreign key to MigrationBatch
- `excel_file_id`: UUID - Foreign key to ExcelFile
- `started_at`: DateTime - File migration start timestamp
- `completed_at`: DateTime - File migration completion timestamp
- `status`: Enum - PENDING, ANALYZING, MIGRATING, COMPLETED, FAILED, ROLLED_BACK
- `records_processed`: Integer - Number of records migrated from this file
- `records_skipped`: Integer - Number of invalid/duplicate records skipped
- `records_failed`: Integer - Number of records that failed migration
- `validation_errors`: JSON - Detailed validation error information
- `rollback_data`: JSON - Information needed for rollback operations

**Relationships**:
- Many-to-one with `MigrationBatch`
- Many-to-one with `ExcelFile`
- One-to-many with `ValidationReport`

**Validation Rules**:
- `records_processed` + `records_skipped` + `records_failed` should equal source record count
- `status` must align with parent batch status
- `completed_at` must be >= `started_at`
- `rollback_data` required when status is COMPLETED

### ValidationReport
**Purpose**: Documents data consistency validation results

**Attributes**:
- `id`: UUID - Unique identifier for the validation report
- `migration_record_id`: UUID - Foreign key to MigrationRecord
- `validation_type`: Enum - SCHEMA_COMPLIANCE, DATA_INTEGRITY, REFERENTIAL_INTEGRITY, DUPLICATE_CHECK
- `passed`: Boolean - Whether validation passed
- `error_count`: Integer - Number of validation errors found
- `warning_count`: Integer - Number of validation warnings
- `details`: JSON - Detailed validation results and error descriptions
- `performed_at`: DateTime - When validation was performed

**Relationships**:
- Many-to-one with `MigrationRecord`

**Validation Rules**:
- `error_count` and `warning_count` must be >= 0
- `passed` should be false if `error_count` > 0
- `details` must contain structured error information

### AuditLog
**Purpose**: Comprehensive audit trail for all migration operations

**Attributes**:
- `id`: UUID - Unique identifier for the audit entry
- `timestamp`: DateTime - When the event occurred
- `operation`: Enum - FILE_DISCOVERED, SCHEMA_ANALYZED, MIGRATION_STARTED, MIGRATION_COMPLETED, ROLLBACK_INITIATED, VALIDATION_PERFORMED
- `entity_type`: Enum - EXCEL_FILE, MIGRATION_BATCH, MIGRATION_RECORD, UNIFIED_SCHEMA
- `entity_id`: UUID - ID of the affected entity
- `user_context`: String - User or system context
- `details`: JSON - Operation-specific details
- `correlation_id`: UUID - For tracking related operations

**Validation Rules**:
- `timestamp` must be current or past
- `entity_id` must reference valid entity
- `correlation_id` used to group related operations

## Entity Relationships Summary

```
UnifiedSchema (1) ←→ (n) TableDefinition
TableDefinition (1) ←→ (n) ColumnMapping
ColumnMapping (n) ←→ (1) ColumnDefinition
ColumnDefinition (n) ←→ (1) ExcelSheet
ExcelSheet (n) ←→ (1) ExcelFile
UnifiedSchema (1) ←→ (n) MigrationBatch
MigrationBatch (1) ←→ (n) MigrationRecord
MigrationRecord (n) ←→ (1) ExcelFile
MigrationRecord (1) ←→ (n) ValidationReport
```

## State Transitions

### ExcelFile Status Flow
```
DISCOVERED → ANALYZING → MIGRATING → COMPLETED
                    ↓         ↓
                  FAILED    FAILED
                    ↓         ↓
               ROLLED_BACK ← ROLLED_BACK
```

### MigrationBatch Status Flow
```
PENDING → RUNNING → COMPLETED
            ↓         ↓
          FAILED    ROLLED_BACK
```

## OEWS-Specific Data Structure

### Real OEWS File Format (Based on Actual Data Analysis)

**Standard OEWS Excel File Structure**:
- **Main Data Sheet**: "All May [YEAR] data" - Contains all employment and wage data
- **Metadata Sheets**: "Field Descriptions", "UpdateTime", "Filler"
- **File Size**: 70-80MB per annual file
- **Record Count**: ~400,000 records per file
- **Column Count**: 32 standardized columns

**Core OEWS Data Columns** (32 total):
1. `AREA` - Geographic area code
2. `AREA_TITLE` - Geographic area name
3. `AREA_TYPE` - Area classification (1=National, 2=State, 4=MSA, etc.)
4. `PRIM_STATE` - Primary state code
5. `NAICS` - Industry code (North American Industry Classification)
6. `NAICS_TITLE` - Industry title
7. `I_GROUP` - Industry group classification
8. `OWN_CODE` - Ownership code (private, government, etc.)
9. `OCC_CODE` - Occupation code (SOC - Standard Occupational Classification)
10. `OCC_TITLE` - Occupation title
11. `O_GROUP` - Occupation group (total, major, minor, broad, detailed)
12. `TOT_EMP` - Total employment
13. `EMP_PRSE` - Employment percent relative standard error
14. `JOBS_1000` - Jobs per 1,000 total employment
15. `LOC_QUOTIENT` - Location quotient
16. `PCT_TOTAL` - Percent of total employment
17. `PCT_RPT` - Percent of establishments reporting
18. `H_MEAN` - Mean hourly wage
19. `A_MEAN` - Mean annual wage
20. `MEAN_PRSE` - Mean wage percent relative standard error
21. `H_PCT10` - 10th percentile hourly wage
22. `H_PCT25` - 25th percentile hourly wage
23. `H_MEDIAN` - Median hourly wage
24. `H_PCT75` - 75th percentile hourly wage
25. `H_PCT90` - 90th percentile hourly wage
26. `A_PCT10` - 10th percentile annual wage
27. `A_PCT25` - 25th percentile annual wage
28. `A_MEDIAN` - Median annual wage
29. `A_PCT75` - 75th percentile annual wage
30. `A_PCT90` - 90th percentile annual wage
31. `ANNUAL` - Annual wage flag
32. `HOURLY` - Hourly wage flag

**Data Type Patterns**:
- **Text Fields**: AREA_TITLE, NAICS_TITLE, OCC_TITLE (VARCHAR)
- **Codes**: AREA, NAICS, OCC_CODE (VARCHAR with specific patterns)
- **Numeric**: TOT_EMP, wages, percentiles (INTEGER, DECIMAL)
- **Special Values**: '#' (suppressed data), '*' (estimated), NaN (not available)

**Key Relationships**:
- **Geographic Hierarchy**: AREA codes represent nested geographic areas
- **Occupation Hierarchy**: OCC_CODE follows SOC hierarchy (major→minor→broad→detailed)
- **Industry Classification**: NAICS codes provide industry groupings
- **Cross-tabulation**: Data combinations of Area × Industry × Occupation

**Migration Considerations**:
- **Duplicate Handling**: Same occupation may appear multiple times per area/industry
- **Suppressed Data**: '#' values need special handling for privacy protection
- **Missing Data**: Handle NaN, empty strings, and asterisk values appropriately
- **Schema Consistency**: Column structure stable across years (2011-2024 verified)

This data model supports all functional requirements including file discovery, schema analysis, migration tracking, validation, and rollback capabilities while maintaining referential integrity and comprehensive audit trails.