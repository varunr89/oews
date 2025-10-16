# Research: Azure SQL Database Deployment

**Feature**: 003-hosted-sql-db
**Date**: 2025-10-12
**Status**: Complete

## 1. Azure SQL Serverless Provisioning

### Decision: Use `azure-mgmt-sql` with `AzureCliCredential`

**Rationale**:
- `azure-identity.AzureCliCredential` automatically uses existing `az login` session (FR-003)
- `azure-mgmt-sql.SqlManagementClient` provides resource management for databases and servers
- Serverless tier specified via `sku=Sku(name='GP_S_Gen5', tier='GeneralPurpose', capacity=1)`

**Implementation Pattern**:
```python
from azure.identity import AzureCliCredential
from azure.mgmt.sql import SqlManagementClient

credential = AzureCliCredential()
sql_client = SqlManagementClient(credential, subscription_id)

# Create server (if not exists)
server = sql_client.servers.begin_create_or_update(
    resource_group_name, server_name, parameters
).result()

# Create serverless database
database = sql_client.databases.begin_create_or_update(
    resource_group_name, server_name, database_name,
    parameters={'sku': Sku(name='GP_S_Gen5', tier='GeneralPurpose', capacity=1)}
).result()
```

**Resource Group Strategy**:
- Option A: Create dedicated resource group per migration (isolated, easy cleanup)
- Option B: Use existing resource group from config (shared resources)
- **SELECTED**: Option A - Easier rollback via single resource group deletion (FR-020)

**Alternatives Considered**:
- Azure CLI subprocess calls: Rejected - less control, harder error handling
- Azure REST API directly: Rejected - more complex, SDK provides better abstractions

### Performance Expectations:
- Server creation: 2-5 minutes (if new)
- Database creation: 1-3 minutes
- Total provisioning: 3-8 minutes for fresh deployment

---

## 2. SQLite to Azure SQL Schema Mapping

### Decision: Type Conversion Matrix with Constraint Preservation

**SQLite → Azure SQL Data Type Mapping**:

| SQLite Type | Azure SQL (T-SQL) Type | Notes |
|-------------|------------------------|-------|
| INTEGER | INT or BIGINT | Use BIGINT if PRIMARY KEY |
| REAL | FLOAT | 8-byte floating point |
| TEXT | NVARCHAR(MAX) | Unicode support |
| BLOB | VARBINARY(MAX) | Binary data |
| NUMERIC | DECIMAL(18,4) | Preserve precision |
| DATE/DATETIME | DATETIME2 | Higher precision |
| BOOLEAN | BIT | SQLite uses INTEGER 0/1 |

**Rationale**:
- NVARCHAR over VARCHAR for Unicode consistency
- MAX lengths to avoid truncation (can optimize later based on profiling)
- DATETIME2 for microsecond precision preservation

**Constraint Translation**:
- PRIMARY KEY: Direct translation (T-SQL supports same syntax)
- UNIQUE: Direct translation with CREATE UNIQUE INDEX
- NOT NULL: Direct translation
- FOREIGN KEY: Translate with CONSTRAINT syntax
- CHECK: Translate to T-SQL CHECK constraint (syntax differs slightly)
- DEFAULT: Translate with CONSTRAINT DEFAULT

**Index Migration**:
- Copy all indexes (CREATE INDEX statements)
- Clustered index automatically created for PRIMARY KEY
- Non-clustered indexes for UNIQUE and explicit CREATE INDEX

**Implementation Approach**:
Use `sqlite3` PRAGMA commands for introspection:
```python
# Get table schema
cursor.execute("PRAGMA table_info(table_name)")
columns = cursor.fetchall()

# Get foreign keys
cursor.execute("PRAGMA foreign_key_list(table_name)")
fkeys = cursor.fetchall()

# Get indexes
cursor.execute("PRAGMA index_list(table_name)")
indexes = cursor.fetchall()
```

**Alternatives Considered**:
- SQLAlchemy reflection: Rejected - already using sqlite3, adds dependency overhead
- Manual schema definition: Rejected - doesn't scale, error-prone

---

## 3. Data Transfer Strategies

### Decision: Batch INSERT with `pyodbc` or `pymssql`

**Selected Approach**: Parameterized batch INSERT with 1000-row batches

**Rationale**:
- Azure SQL INSERVALUES limits: ~1000 rows per INSERT statement
- Batch size balances memory usage vs. network round trips
- Parameterized queries prevent SQL injection, handle escaping

**Implementation Pattern**:
```python
import pyodbc  # or pymssql

# Batch insert
batch_size = 1000
cursor = azure_conn.cursor()

for i in range(0, len(rows), batch_size):
    batch = rows[i:i+batch_size]
    placeholders = ','.join(['(?' + ',?' * (len(batch[0])-1) + ')' for _ in batch])
    query = f"INSERT INTO {table} VALUES {placeholders}"
    flat_values = [val for row in batch for val in row]
    cursor.execute(query, flat_values)
    azure_conn.commit()
```

**Progress Tracking**:
- Track rows transferred per table
- Emit progress event every 5 seconds (FR-012)
- Calculate percentage: (transferred_rows / total_rows) * 100

**Connection Management**:
- Use connection string from Azure SQL Management API response
- Connection format: `pyodbc` with ODBC Driver 17/18 for SQL Server
- Alternative: `pymssql` if ODBC driver unavailable (pure Python)

**Performance Expectations**:
- Transfer rate: 5,000-10,000 rows/second (depends on row size, network)
- 1GB database (~10M rows): 15-30 minutes transfer time

**Alternatives Considered**:
- BCP utility: Rejected - requires external tool, not cross-platform
- SQL Server BULK INSERT: Rejected - requires file upload to Azure, complex
- pandas to_sql: Rejected - slower than direct parameterized inserts for large data

---

## 4. Error Handling & Rollback

### Decision: Transaction-per-table + Resource Group Cleanup

**Rollback Strategy**:
- **Schema Migration**: Wrap CREATE statements in try/catch, rollback Azure SQL transaction on failure
- **Data Transfer**: Use transaction per table (commit after each table completes)
- **Resource Cleanup**: Delete resource group via Azure SDK (cascades to all resources)

**Implementation Pattern**:
```python
from azure.mgmt.resource import ResourceManagementClient

# Track created resources
resources_created = []

try:
    # Provisioning
    rg = resource_client.resource_groups.create_or_update(rg_name, {...})
    resources_created.append(('resource_group', rg_name))

    server = sql_client.servers.begin_create_or_update(...).result()
    resources_created.append(('server', server_name))

    db = sql_client.databases.begin_create_or_update(...).result()
    resources_created.append(('database', db_name))

    # Migration
    for table in tables:
        with azure_conn.cursor() as cursor:
            cursor.execute(f"CREATE TABLE {table} ...")
            # Load data
            azure_conn.commit()

except Exception as e:
    # Rollback
    logger.error(f"Deployment failed: {e}")
    rollback(resources_created)
    raise

def rollback(resources):
    for resource_type, resource_name in reversed(resources):
        if resource_type == 'resource_group':
            resource_client.resource_groups.begin_delete(resource_name).result()
```

**Partial Failure Handling**:
- If table schema creation fails: Rollback entire deployment (FR-020)
- If data transfer fails mid-table: Rollback entire deployment
- If rollback itself fails: Log detailed manual cleanup instructions (FR-023)

**Transaction Scope**:
- SQLite: Read-only transactions (no changes to source)
- Azure SQL: One transaction per table for schema + data
- Azure Resources: No transaction support - manual cleanup on failure

**Alternatives Considered**:
- Full database-level transaction: Rejected - Azure SQL doesn't support transaction across CREATE DATABASE
- Keep partial migration: Rejected - violates FR-020 (automatic rollback)

---

## 5. Data Consistency Validation

### Decision: Row Count + Sampled Hash Comparison

**Validation Steps**:
1. **Table Existence**: Compare table lists (SQLite PRAGMA vs. Azure SQL INFORMATION_SCHEMA)
2. **Row Counts**: `SELECT COUNT(*) FROM table` on both sides
3. **Sample Validation**: Hash 10% of rows (random sampling) and compare

**Sample Hashing Strategy**:
```python
import hashlib
import random

def validate_table_sample(sqlite_conn, azure_conn, table, sample_pct=0.10):
    # Get total rows
    total_rows = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    sample_size = int(total_rows * sample_pct)

    # Random row sampling (using ROWID for SQLite)
    sqlite_rows = sqlite_conn.execute(f"""
        SELECT * FROM {table}
        WHERE ROWID IN (SELECT ROWID FROM {table} ORDER BY RANDOM() LIMIT {sample_size})
    """).fetchall()

    azure_rows = azure_conn.execute(f"""
        SELECT TOP {sample_size} * FROM {table} ORDER BY NEWID()
    """).fetchall()

    # Hash comparison
    sqlite_hash = hashlib.sha256(str(sorted(sqlite_rows)).encode()).hexdigest()
    azure_hash = hashlib.sha256(str(sorted(azure_rows)).encode()).hexdigest()

    return sqlite_hash == azure_hash
```

**Rationale**:
- Row count catches obvious failures (missing data)
- 10% sample balances thoroughness vs. performance (FR-016)
- Hashing entire row content catches corruption/conversion errors

**Performance Expectations**:
- Row count queries: <5 seconds per table
- Sample hash validation: 1-2 minutes per GB (10% sampling)
- Total validation: 5-10 minutes for 5GB database

**Validation Report** (FR-017):
```json
{
  "timestamp": "2025-10-12T10:30:00Z",
  "status": "PASS" | "FAIL",
  "tables_validated": 15,
  "checks": [
    {"table": "employees", "row_count_match": true, "sample_hash_match": true},
    {"table": "departments", "row_count_match": true, "sample_hash_match": false, "discrepancy": "Hash mismatch in sample"}
  ]
}
```

**Alternatives Considered**:
- Full data comparison: Rejected - too slow for large databases
- Schema-only validation: Rejected - doesn't catch data corruption (insufficient per FR-016)

---

## 6. Configuration Management

### Decision: `.env` file with `python-dotenv`

**Configuration Parameters**:
```env
# Azure Configuration
AZURE_REGION=eastus
AZURE_SUBSCRIPTION_ID=<auto-detected from Azure CLI>
AZURE_RESOURCE_GROUP_PREFIX=oews-migration

# Migration Settings
BATCH_SIZE=1000
VALIDATION_SAMPLE_PCT=0.10
PROGRESS_UPDATE_INTERVAL_SEC=5

# Database Settings
AZURE_SQL_SERVER_ADMIN=sqladmin
AZURE_SQL_SERVER_ADMIN_PASSWORD=<generated secure password>
```

**Rationale**:
- `.env` file standard in Python projects
- `python-dotenv` already in dependencies (used in feature 002)
- Easy to validate and provide clear error messages (FR-025)

**Region Validation**:
- Fetch valid regions from Azure SDK: `sql_client.capabilities.list_by_location()`
- Compare user config against valid list
- Provide helpful error if invalid (FR-024, FR-025)

**Alternatives Considered**:
- config.json: Rejected - .env more standard for credentials
- Command-line args only: Rejected - doesn't meet FR-006 requirement

---

## 7. Naming Strategy

### Decision: Filename-based with sanitization

**Database Name Generation**:
```python
import re
from pathlib import Path

def generate_database_name(db_path: str) -> str:
    # Extract filename without extension
    filename = Path(db_path).stem  # "oews.db" → "oews"

    # Sanitize: lowercase, replace non-alphanumeric with hyphen
    sanitized = re.sub(r'[^a-z0-9]+', '-', filename.lower())

    # Append suffix
    db_name = f"{sanitized}-azure"

    # Azure SQL name constraints: 1-128 chars, alphanumeric + hyphen
    return db_name[:128]
```

**Examples**:
- `oews.db` → `oews-azure`
- `My_Data_2024.sqlite` → `my-data-2024-azure`
- `test.db` → `test-azure`

**Collision Handling**:
- Check if database exists: `sql_client.databases.get()`
- If exists: Error with clear message suggesting manual deletion or different filename (edge case)

**Server Naming**:
- Pattern: `{db_name}-server-{random_suffix}` (ensures uniqueness across Azure)
- Random suffix: 8-char alphanumeric (uuid4 hex digest)

**Alternatives Considered**:
- User-provided name: Rejected - violates FR-007 (auto-generate)
- Timestamp-based: Rejected - less intuitive than source filename

---

## Summary of Resolved Clarifications

| Item | Resolution |
|------|------------|
| Progress Update Frequency | Every 5 seconds during long operations |
| Database Size Limits | Initial target: 5GB (expandable with performance tuning) |
| Performance Targets | Provisioning: 3-8min, Transfer: 5-10k rows/sec, Validation: 5-10min |
| Network Failure Recovery | Deferred to future enhancement - MVP uses automatic rollback |

---

## Technology Stack Final

- **Azure SDK**: `azure-identity==1.15.0`, `azure-mgmt-sql==4.0.0`, `azure-mgmt-resource==23.0.0`
- **Database Connectivity**: `pyodbc>=5.0.0` (primary) or `pymssql>=2.2.0` (fallback)
- **Configuration**: `python-dotenv>=1.0.0` (already in project)
- **CLI**: Extend existing `click`-based CLI in `src/cli/commands.py`
- **Testing**: `pytest>=7.0.0`, `pytest-mock>=3.12.0` for Azure SDK mocking

---

**Status**: Research complete - ready for Phase 1 Design & Contracts
