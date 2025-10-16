# Contract: ValidationService

**Feature**: 003-hosted-sql-db
**Requirements**: FR-013, FR-014, FR-015, FR-016, FR-017

## Purpose

Validate data consistency between SQLite and Azure SQL databases.

## Interface

### Method: `validate_migration(source_conn: sqlite3.Connection, target_conn: pyodbc.Connection, table_names: List[str], sample_pct: float) -> ValidationReport`

**Description**: Perform complete migration validation

**Inputs**:
- `source_conn`: sqlite3.Connection - SQLite connection
- `target_conn`: pyodbc.Connection - Azure SQL connection
- `table_names`: List[str] - Tables to validate
- `sample_pct`: float - Percentage of rows to sample for hash validation (0.0-1.0)

**Outputs**:
- `ValidationReport` - Complete validation results (see data-model.md)

**Behavior**:
- Validate all tables exist in both databases
- For each table:
  - Validate row counts match
  - Perform sample hash validation
- Generate comprehensive ValidationReport
- Set overall status (PASS/FAIL)

**Errors**: None (errors captured in ValidationReport)

**Requirements Mapping**:
- FR-013: Perform consistency validation after migration
- FR-017: Generate validation report

---

### Method: `validate_table_exists(conn, table_name: str, db_type: str) -> bool`

**Description**: Check if table exists in database

**Inputs**:
- `conn`: Database connection (sqlite3 or pyodbc)
- `table_name`: str
- `db_type`: str - "sqlite" or "azure_sql"

**Outputs**:
- `bool` - True if table exists

**Behavior**:
- For SQLite: Query `sqlite_master`
- For Azure SQL: Query `INFORMATION_SCHEMA.TABLES`

**Requirements Mapping**:
- FR-014: Verify all tables exist

---

### Method: `validate_row_counts(source_conn: sqlite3.Connection, target_conn: pyodbc.Connection, table_name: str) -> RowCountResult`

**Description**: Compare row counts between databases

**Inputs**:
- `source_conn`: sqlite3.Connection
- `target_conn`: pyodbc.Connection
- `table_name`: str

**Outputs**:
- `RowCountResult`:
  - `table_name`: str
  - `source_count`: int
  - `target_count`: int
  - `match`: bool

**Behavior**:
- Execute `SELECT COUNT(*) FROM {table}` on both databases
- Compare counts
- Return result

**Requirements Mapping**:
- FR-015: Verify row counts match

---

### Method: `validate_sample_hash(source_conn: sqlite3.Connection, target_conn: pyodbc.Connection, table_name: str, sample_pct: float) -> HashValidationResult`

**Description**: Hash a random sample of rows and compare

**Inputs**:
- `source_conn`: sqlite3.Connection
- `target_conn`: pyodbc.Connection
- `table_name`: str
- `sample_pct`: float - Percentage to sample (e.g., 0.10 for 10%)

**Outputs**:
- `HashValidationResult`:
  - `table_name`: str
  - `sample_size`: int
  - `source_hash`: str
  - `target_hash`: str
  - `match`: bool

**Behavior**:
- Calculate sample size: `total_rows * sample_pct`
- Query random sample from SQLite: `SELECT * FROM {table} ORDER BY RANDOM() LIMIT {sample_size}`
- Query random sample from Azure SQL: `SELECT TOP {sample_size} * FROM {table} ORDER BY NEWID()`
- Sort rows to ensure consistent ordering
- Hash row content using SHA256
- Compare hashes

**Errors**:
- `ValidationException`: Failed to query or hash data

**Requirements Mapping**:
- FR-016: Verify data integrity using hash comparison on 10% sample

---

### Method: `generate_validation_report(table_results: List[TableValidationResult], job_id: str) -> ValidationReport`

**Description**: Create final validation report

**Inputs**:
- `table_results`: List[TableValidationResult]
- `job_id`: str

**Outputs**:
- `ValidationReport` (see data-model.md)

**Behavior**:
- Aggregate table-level results
- Determine overall status (PASS if all tables valid)
- Add timestamp and duration
- Format for JSON export

**Requirements Mapping**:
- FR-017: Generate validation report

---

## Contract Test Assertions

```python
def test_validate_migration_all_pass():
    # Given: Databases with matching data
    service = ValidationService()
    source_conn = sqlite3.connect("source.db")
    target_conn = pyodbc.connect(azure_connection_string)

    # When: Validate migration
    report = service.validate_migration(source_conn, target_conn, ["employees"], 0.10)

    # Then: Validation passes
    assert report.status == ValidationStatus.PASS
    assert len(report.table_results) == 1
    assert report.table_results[0].is_valid() == True

def test_validate_migration_row_count_mismatch():
    # Given: Databases with different row counts
    service = ValidationService()

    # When: Validate migration
    report = service.validate_migration(source_conn, target_conn, ["employees"], 0.10)

    # Then: Validation fails
    assert report.status == ValidationStatus.FAIL
    assert any("row count" in d.lower() for d in report.table_results[0].discrepancies)

def test_validate_table_exists_sqlite():
    # Given: SQLite connection with table
    service = ValidationService()
    conn = sqlite3.connect("test.db")

    # When: Check table exists
    exists = service.validate_table_exists(conn, "employees", "sqlite")

    # Then: Returns True
    assert exists == True

def test_validate_row_counts_match():
    # Given: Tables with same row count
    service = ValidationService()

    # When: Validate row counts
    result = service.validate_row_counts(source_conn, target_conn, "employees")

    # Then: Counts match
    assert result.source_count == result.target_count
    assert result.match == True

def test_validate_sample_hash_match():
    # Given: Tables with identical data
    service = ValidationService()

    # When: Validate sample hash
    result = service.validate_sample_hash(source_conn, target_conn, "employees", 0.10)

    # Then: Hashes match
    assert result.source_hash == result.target_hash
    assert result.match == True
    # Sample size is 10% of total rows
    assert result.sample_size > 0

def test_generate_validation_report():
    # Given: Table validation results
    service = ValidationService()
    table_results = [TableValidationResult(...)]

    # When: Generate report
    report = service.generate_validation_report(table_results, "job-123")

    # Then: Report created
    assert report.job_id == "job-123"
    assert report.timestamp is not None
    assert len(report.table_results) == len(table_results)
```
