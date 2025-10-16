# Contract: SchemaMigrationService

**Feature**: 003-hosted-sql-db
**Requirements**: FR-008, FR-009

## Purpose

Extract SQLite schema and convert to Azure SQL T-SQL schema.

## Interface

### Method: `extract_schema(sqlite_conn: sqlite3.Connection) -> List[SchemaDefinition]`

**Description**: Extract all table schemas from SQLite database

**Inputs**:
- `sqlite_conn`: sqlite3.Connection - Open SQLite database connection

**Outputs**:
- `List[SchemaDefinition]` - One schema per table (see data-model.md)

**Behavior**:
- Query `sqlite_master` for all tables (exclude internal sqlite_ tables)
- For each table:
  - Execute `PRAGMA table_info(table_name)` for columns
  - Execute `PRAGMA foreign_key_list(table_name)` for foreign keys
  - Execute `PRAGMA index_list(table_name)` and `PRAGMA index_info(index_name)` for indexes
  - Parse CHECK constraints from `CREATE TABLE` SQL
- Build `SchemaDefinition` objects with all metadata

**Errors**:
- `SchemaExtractionException`: Failed to read SQLite schema

**Requirements Mapping**:
- FR-008: Migrate complete schema including tables, columns, data types, constraints

---

### Method: `convert_schema(schema: SchemaDefinition) -> str`

**Description**: Convert SQLite schema to Azure SQL T-SQL DDL

**Inputs**:
- `schema`: SchemaDefinition

**Outputs**:
- `str` - T-SQL CREATE TABLE statement with all constraints

**Behavior**:
- Generate CREATE TABLE statement with converted column types
- Apply data type mapping (see data-model.md and research.md):
  - INTEGER → INT (or BIGINT if PK)
  - REAL → FLOAT
  - TEXT → NVARCHAR(MAX)
  - BLOB → VARBINARY(MAX)
  - NUMERIC → DECIMAL(18,4)
  - DATE/DATETIME → DATETIME2
  - BOOLEAN → BIT
- Add PRIMARY KEY constraint
- Generate ALTER TABLE statements for foreign keys
- Generate CREATE INDEX statements
- Generate CHECK constraints (translate syntax differences)

**Errors**:
- `UnsupportedTypeException`: Unsupported SQLite type encountered

**Requirements Mapping**:
- FR-008: Migrate complete schema
- FR-009: Handle data type conversions

---

### Method: `apply_schema(azure_conn, schemas: List[SchemaDefinition]) -> ApplyResult`

**Description**: Execute T-SQL statements to create schema in Azure SQL

**Inputs**:
- `azure_conn`: pyodbc.Connection - Azure SQL connection
- `schemas`: List[SchemaDefinition] - Schemas to create

**Behavior**:
- Determine table creation order based on foreign key dependencies
- For each table (in dependency order):
  - Execute CREATE TABLE statement
  - Execute CREATE INDEX statements
- After all tables created: apply foreign key constraints
- Wrap in transaction (rollback on any failure)

**Outputs**:
- `ApplyResult`:
  - `success`: bool
  - `tables_created`: List[str]
  - `indexes_created`: List[str]
  - `error_message`: Optional[str]

**Errors**:
- `SchemaApplicationException`: Failed to apply schema to Azure SQL
- `CircularDependencyException`: Tables have circular foreign key dependencies

**Requirements Mapping**:
- FR-008: Migrate complete schema

---

### Method: `get_table_creation_order(schemas: List[SchemaDefinition]) -> List[str]`

**Description**: Determine correct order to create tables based on foreign keys

**Inputs**:
- `schemas`: List[SchemaDefinition]

**Outputs**:
- `List[str]` - Table names in dependency order (tables with no dependencies first)

**Behavior**:
- Build dependency graph from foreign key relationships
- Perform topological sort
- If circular dependencies detected: raise exception

**Errors**:
- `CircularDependencyException`: Circular foreign keys found

**Requirements Mapping**:
- FR-008: Migrate schema including foreign key constraints

---

## Contract Test Assertions

```python
def test_extract_schema_all_tables():
    # Given: SQLite database with 3 tables
    service = SchemaMigrationService()
    conn = sqlite3.connect("test.db")

    # When: Extract schema
    schemas = service.extract_schema(conn)

    # Then: All tables extracted
    assert len(schemas) == 3
    assert all(isinstance(s, SchemaDefinition) for s in schemas)

def test_convert_schema_type_mapping():
    # Given: SchemaDefinition with various SQLite types
    service = SchemaMigrationService()
    schema = SchemaDefinition(
        table_name="test",
        columns=[
            ColumnDefinition(name="id", sqlite_type="INTEGER", ...),
            ColumnDefinition(name="name", sqlite_type="TEXT", ...),
            ColumnDefinition(name="amount", sqlite_type="REAL", ...),
        ]
    )

    # When: Convert schema
    tsql = service.convert_schema(schema)

    # Then: Types correctly mapped
    assert "INT" in tsql or "BIGINT" in tsql
    assert "NVARCHAR(MAX)" in tsql
    assert "FLOAT" in tsql

def test_apply_schema_success():
    # Given: Azure SQL connection and schemas
    service = SchemaMigrationService()
    azure_conn = pyodbc.connect(connection_string)
    schemas = [SchemaDefinition(...)]

    # When: Apply schema
    result = service.apply_schema(azure_conn, schemas)

    # Then: Schema created successfully
    assert result.success == True
    assert len(result.tables_created) == len(schemas)

def test_get_table_creation_order_with_dependencies():
    # Given: Tables with foreign key dependencies (orders -> customers)
    service = SchemaMigrationService()
    schemas = [
        SchemaDefinition(table_name="orders", foreign_keys=[...]),  # references customers
        SchemaDefinition(table_name="customers", foreign_keys=[]),  # no dependencies
    ]

    # When: Get creation order
    order = service.get_table_creation_order(schemas)

    # Then: Customers before orders
    assert order == ["customers", "orders"]
```
