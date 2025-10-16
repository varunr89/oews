# Data Model: Azure SQL Database Deployment

**Feature**: 003-hosted-sql-db
**Date**: 2025-10-12
**Status**: Complete

## Overview

This document defines the data structures and domain entities for the Azure SQL database deployment feature. These entities model the migration process, configuration, validation results, and state tracking.

---

## 1. DeploymentConfiguration

**Purpose**: Configuration settings for Azure deployment

**Attributes**:
- `source_db_path`: str - Absolute path to local SQLite database file
- `azure_region`: str - Azure region for resource deployment (e.g., "eastus")
- `subscription_id`: str - Azure subscription ID (from Azure CLI)
- `resource_group_name`: str - Name of Azure resource group (auto-generated or specified)
- `database_name`: str - Target Azure SQL database name (auto-generated from filename)
- `server_name`: str - Azure SQL server name (auto-generated with random suffix)
- `batch_size`: int - Rows per batch for data transfer (default: 1000)
- `validation_sample_pct`: float - Percentage of rows to sample for validation (default: 0.10)
- `progress_interval_sec`: int - Seconds between progress updates (default: 5)

**Validation Rules**:
- `source_db_path` must exist and be a valid SQLite file
- `azure_region` must be in valid Azure regions list
- `batch_size` must be > 0 and <= 10000
- `validation_sample_pct` must be between 0.01 and 1.0
- `progress_interval_sec` must be > 0

**Source**: Loaded from `.env` file and command-line arguments

---

## 2. SchemaDefinition

**Purpose**: Represents database schema structure for migration

**Attributes**:
- `table_name`: str - Name of database table
- `columns`: List[ColumnDefinition] - Column definitions
- `primary_key`: Optional[List[str]] - Column names forming primary key
- `foreign_keys`: List[ForeignKeyConstraint] - Foreign key relationships
- `indexes`: List[IndexDefinition] - Index definitions
- `check_constraints`: List[CheckConstraint] - CHECK constraints

**Methods**:
- `to_tsql() -> str` - Generate T-SQL CREATE TABLE statement for Azure SQL
- `from_sqlite(conn, table_name) -> SchemaDefinition` - Extract schema from SQLite

**Relationships**:
- Contains multiple `ColumnDefinition` objects
- Contains multiple `ForeignKeyConstraint` objects
- Contains multiple `IndexDefinition` objects

---

## 3. ColumnDefinition

**Purpose**: Defines a single table column with type mapping

**Attributes**:
- `name`: str - Column name
- `sqlite_type`: str - Original SQLite data type (TEXT, INTEGER, REAL, BLOB, NUMERIC)
- `azure_type`: str - Mapped Azure SQL data type (NVARCHAR, INT, FLOAT, VARBINARY, DECIMAL, DATETIME2, BIT)
- `nullable`: bool - Whether column allows NULL values
- `default_value`: Optional[str] - Default value expression
- `is_primary_key`: bool - Whether column is part of primary key

**Type Mapping** (from research.md):
- INTEGER → INT (or BIGINT if primary key)
- REAL → FLOAT
- TEXT → NVARCHAR(MAX)
- BLOB → VARBINARY(MAX)
- NUMERIC → DECIMAL(18,4)
- DATE/DATETIME → DATETIME2
- BOOLEAN (INTEGER 0/1) → BIT

**Methods**:
- `to_tsql() -> str` - Generate T-SQL column definition

---

## 4. ForeignKeyConstraint

**Purpose**: Defines foreign key relationships between tables

**Attributes**:
- `name`: str - Constraint name (auto-generated if not specified)
- `table`: str - Source table name
- `columns`: List[str] - Source column names
- `referenced_table`: str - Target table name
- `referenced_columns`: List[str] - Target column names
- `on_delete`: Optional[str] - ON DELETE action (CASCADE, SET NULL, etc.)
- `on_update`: Optional[str] - ON UPDATE action

**Methods**:
- `to_tsql() -> str` - Generate T-SQL ALTER TABLE ADD CONSTRAINT statement

---

## 5. IndexDefinition

**Purpose**: Defines table indexes for performance

**Attributes**:
- `name`: str - Index name
- `table`: str - Table name
- `columns`: List[str] - Indexed column names
- `unique`: bool - Whether index enforces uniqueness
- `clustered`: bool - Whether index is clustered (Azure SQL specific)

**Methods**:
- `to_tsql() -> str` - Generate T-SQL CREATE INDEX statement

**Note**: Primary key automatically creates clustered index in Azure SQL

---

## 6. CheckConstraint

**Purpose**: Defines CHECK constraints on columns

**Attributes**:
- `name`: str - Constraint name
- `table`: str - Table name
- `expression`: str - CHECK expression (translated from SQLite to T-SQL syntax)

**Methods**:
- `to_tsql() -> str` - Generate T-SQL ALTER TABLE ADD CONSTRAINT statement

---

## 7. MigrationJob

**Purpose**: Tracks the state of a deployment operation

**Attributes**:
- `job_id`: str - Unique identifier (UUID)
- `start_time`: datetime - When deployment started
- `end_time`: Optional[datetime] - When deployment completed/failed
- `status`: MigrationStatus - Current status (enum)
- `current_phase`: str - Current operation (e.g., "provisioning", "schema_migration", "data_transfer", "validation")
- `tables_migrated`: int - Count of tables successfully migrated
- `total_tables`: int - Total number of tables to migrate
- `rows_transferred`: int - Total rows transferred so far
- `total_rows`: int - Total rows to transfer
- `error_message`: Optional[str] - Error details if failed
- `resources_created`: List[AzureResource] - Track created Azure resources for rollback
- `configuration`: DeploymentConfiguration - Deployment configuration used

**MigrationStatus Enum**:
- `INITIALIZING` - Validating configuration
- `PROVISIONING` - Creating Azure resources
- `MIGRATING_SCHEMA` - Creating tables/constraints
- `TRANSFERRING_DATA` - Copying data
- `VALIDATING` - Running consistency checks
- `COMPLETED` - Successfully finished
- `FAILED` - Encountered error
- `ROLLING_BACK` - Cleaning up after failure
- `ROLLBACK_COMPLETE` - Rollback finished
- `ROLLBACK_FAILED` - Rollback encountered error

**Methods**:
- `update_progress(phase: str, progress_pct: float) -> None` - Update current phase and progress
- `add_resource(resource: AzureResource) -> None` - Track created Azure resource
- `to_dict() -> dict` - Serialize for logging/reporting

---

## 8. AzureResource

**Purpose**: Represents a created Azure resource for tracking/rollback

**Attributes**:
- `resource_type`: str - Type of resource (e.g., "resource_group", "server", "database")
- `resource_id`: str - Azure resource ID
- `name`: str - Resource name
- `created_at`: datetime - When resource was created

**Methods**:
- `delete(azure_client) -> None` - Delete this resource via Azure SDK

---

## 9. ValidationReport

**Purpose**: Results of data consistency validation

**Attributes**:
- `job_id`: str - Associated migration job ID
- `timestamp`: datetime - When validation was performed
- `status`: ValidationStatus - Overall validation result (enum)
- `tables_validated`: int - Number of tables checked
- `table_results`: List[TableValidationResult] - Per-table validation details
- `total_duration_sec`: float - Time taken for validation

**ValidationStatus Enum**:
- `PASS` - All checks passed
- `FAIL` - One or more checks failed
- `PARTIAL` - Some tables validated, others failed

**Methods**:
- `to_dict() -> dict` - Serialize for reporting (FR-017)
- `to_json() -> str` - JSON representation for file export
- `get_failed_tables() -> List[str]` - List tables that failed validation

---

## 10. TableValidationResult

**Purpose**: Validation results for a single table

**Attributes**:
- `table_name`: str - Table name
- `exists_in_source`: bool - Table exists in SQLite
- `exists_in_target`: bool - Table exists in Azure SQL
- `row_count_source`: int - Row count in SQLite
- `row_count_target`: int - Row count in Azure SQL
- `row_count_match`: bool - Whether row counts match
- `sample_hash_source`: str - Hash of sample rows from SQLite
- `sample_hash_target`: str - Hash of sample rows from Azure SQL
- `sample_hash_match`: bool - Whether sample hashes match
- `discrepancies`: List[str] - Descriptions of any mismatches

**Methods**:
- `is_valid() -> bool` - Returns True if all checks pass
- `to_dict() -> dict` - Serialize for reporting

---

## 11. ProgressEvent

**Purpose**: Real-time progress updates during deployment (FR-012)

**Attributes**:
- `job_id`: str - Associated migration job ID
- `timestamp`: datetime - When event occurred
- `phase`: str - Current phase (matches MigrationJob.current_phase)
- `message`: str - Human-readable status message
- `progress_pct`: float - Overall completion percentage (0.0 to 100.0)
- `current_table`: Optional[str] - Table currently being processed
- `rows_processed`: int - Rows processed so far
- `estimated_time_remaining_sec`: Optional[float] - ETA to completion

**Methods**:
- `format_message() -> str` - Format for console output

**Example Messages**:
- "Authenticating with Azure CLI..."
- "Provisioning Azure SQL Server (oews-azure-server-abc123)..."
- "Creating table employees (5/15)..."
- "Transferring data to employees: 5000/10000 rows (50%)..."
- "Validating table employees..."
- "Migration completed successfully!"
- "Error: Database file not found at /path/to/db.sqlite"

---

## Entity Relationships

```
DeploymentConfiguration
  └─> Used by MigrationJob

MigrationJob
  ├─> Contains DeploymentConfiguration
  ├─> Creates multiple AzureResource (tracked for rollback)
  └─> Produces ValidationReport

SchemaDefinition
  ├─> Contains multiple ColumnDefinition
  ├─> Contains multiple ForeignKeyConstraint
  ├─> Contains multiple IndexDefinition
  └─> Contains multiple CheckConstraint

ValidationReport
  ├─> Linked to MigrationJob (via job_id)
  └─> Contains multiple TableValidationResult

ProgressEvent
  └─> Linked to MigrationJob (via job_id)
```

---

## State Transitions

### MigrationJob Status Flow

```
INITIALIZING
  ↓
PROVISIONING (creates AzureResource entries)
  ↓
MIGRATING_SCHEMA
  ↓
TRANSFERRING_DATA
  ↓
VALIDATING (creates ValidationReport)
  ↓
COMPLETED (success)

Any state →
  FAILED
    ↓
  ROLLING_BACK (deletes AzureResource entries)
    ↓
  ROLLBACK_COMPLETE or ROLLBACK_FAILED
```

---

## Storage Strategy

**During Execution**:
- All entities held in memory (Python objects)
- MigrationJob state written to log file incrementally
- ProgressEvents emitted to console in real-time

**Persistence**:
- ValidationReport saved as JSON file: `validation_report_{job_id}.json`
- MigrationJob final state logged: `deployment_{job_id}.log`
- No database persistence required (one-time deployment tool)

---

## Implementation Notes

1. **Type Conversions**: Use `ColumnDefinition` mapping table from research.md
2. **Schema Extraction**: Use SQLite PRAGMA commands (`table_info`, `foreign_key_list`, `index_list`)
3. **Validation Sampling**: Use `RANDOM()` (SQLite) and `NEWID()` (Azure SQL) for row sampling
4. **Progress Calculation**: `(rows_transferred / total_rows) * 100`
5. **Error Context**: Include resource names/IDs in all error messages for debugging

---

**Status**: Data model complete - ready for contract generation
