# Contract: DataTransferService

**Feature**: 003-hosted-sql-db
**Requirements**: FR-010, FR-011, FR-012

## Purpose

Transfer data from SQLite to Azure SQL in batches with progress tracking.

## Interface

### Method: `transfer_table(source_conn: sqlite3.Connection, target_conn: pyodbc.Connection, table_name: str, batch_size: int, progress_callback: Callable) -> TransferResult`

**Description**: Transfer all data from one table

**Inputs**:
- `source_conn`: sqlite3.Connection - SQLite connection
- `target_conn`: pyodbc.Connection - Azure SQL connection
- `table_name`: str - Table to transfer
- `batch_size`: int - Rows per batch (default: 1000)
- `progress_callback`: Callable[[int, int], None] - Function to call with (rows_transferred, total_rows)

**Outputs**:
- `TransferResult`:
  - `table_name`: str
  - `rows_transferred`: int
  - `duration_sec`: float
  - `success`: bool
  - `error_message`: Optional[str]

**Behavior**:
- Count total rows in source table: `SELECT COUNT(*) FROM {table}`
- Fetch rows from SQLite in batches: `SELECT * FROM {table} LIMIT {batch_size} OFFSET {offset}`
- For each batch:
  - Build parameterized INSERT statement with placeholders
  - Execute INSERT on Azure SQL connection
  - Commit transaction after each batch
  - Call progress_callback with updated count
- Return result with transfer statistics

**Errors**:
- `DataTransferException`: Transfer failed (e.g., constraint violation, network error)

**Requirements Mapping**:
- FR-010: Migrate all data from all tables
- FR-011: Preserve data integrity (transaction per table)
- FR-012: Progress updates

---

### Method: `transfer_all_tables(source_conn: sqlite3.Connection, target_conn: pyodbc.Connection, table_names: List[str], batch_size: int, progress_callback: Callable) -> AllTablesResult`

**Description**: Transfer data for all tables

**Inputs**:
- `source_conn`: sqlite3.Connection
- `target_conn`: pyodbc.Connection
- `table_names`: List[str] - Tables to transfer (in correct order)
- `batch_size`: int
- `progress_callback`: Callable[[ProgressEvent], None] - Function to emit progress events

**Outputs**:
- `AllTablesResult`:
  - `total_rows_transferred`: int
  - `tables_completed`: List[str]
  - `duration_sec`: float
  - `success`: bool
  - `failed_table`: Optional[str] - First table that failed (if any)

**Behavior**:
- For each table in order:
  - Call `transfer_table()` with progress callback
  - Emit ProgressEvent with current table, percentage complete
  - If any table fails: raise exception (don't continue to next table)
- Calculate overall progress: (tables_completed / total_tables) * 100
- Emit progress event every 5 seconds (FR-012)

**Errors**:
- `DataTransferException`: Any table transfer failed

**Requirements Mapping**:
- FR-010: Migrate all data
- FR-012: Display progress updates

---

### Method: `build_insert_statement(table_name: str, column_count: int, batch_size: int) -> str`

**Description**: Build parameterized INSERT statement for batch insert

**Inputs**:
- `table_name`: str
- `column_count`: int - Number of columns
- `batch_size`: int - Number of rows to insert

**Outputs**:
- `str` - T-SQL INSERT statement with placeholders

**Example Output**:
```sql
INSERT INTO employees VALUES (?, ?, ?), (?, ?, ?), ...
```

**Behavior**:
- Generate placeholders: `(?, ?, ...)` for each row
- Repeat for `batch_size` rows
- Return full INSERT statement

**Requirements Mapping**:
- FR-010: Migrate data (implementation detail)

---

## Contract Test Assertions

```python
def test_transfer_table_success():
    # Given: Source and target connections, table with 1000 rows
    service = DataTransferService()
    source_conn = sqlite3.connect("source.db")
    target_conn = pyodbc.connect(azure_connection_string)
    progress_calls = []

    # When: Transfer table
    result = service.transfer_table(
        source_conn,
        target_conn,
        "employees",
        batch_size=100,
        progress_callback=lambda rows, total: progress_calls.append((rows, total))
    )

    # Then: All rows transferred
    assert result.success == True
    assert result.rows_transferred == 1000
    # Progress callback called 10 times (1000 rows / 100 batch_size)
    assert len(progress_calls) == 10

def test_transfer_table_with_constraint_violation():
    # Given: Target table has constraint that will fail
    service = DataTransferService()

    # When: Transfer table with invalid data
    # Then: Raises exception
    with pytest.raises(DataTransferException):
        service.transfer_table(source_conn, target_conn, "employees", 1000, lambda r, t: None)

def test_transfer_all_tables_success():
    # Given: Multiple tables to transfer
    service = DataTransferService()
    progress_events = []

    # When: Transfer all tables
    result = service.transfer_all_tables(
        source_conn,
        target_conn,
        ["customers", "orders", "products"],
        batch_size=1000,
        progress_callback=lambda event: progress_events.append(event)
    )

    # Then: All tables transferred
    assert result.success == True
    assert len(result.tables_completed) == 3
    # Progress events emitted
    assert len(progress_events) > 0

def test_build_insert_statement():
    # Given: Table info
    service = DataTransferService()

    # When: Build insert statement
    sql = service.build_insert_statement("test_table", column_count=3, batch_size=2)

    # Then: Correct SQL generated
    assert "INSERT INTO test_table VALUES" in sql
    assert "(?, ?, ?), (?, ?, ?)" in sql  # 2 rows * 3 columns
```
