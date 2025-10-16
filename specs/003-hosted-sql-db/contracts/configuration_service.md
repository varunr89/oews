# Contract: ConfigurationService

**Feature**: 003-hosted-sql-db
**Requirements**: FR-001, FR-002, FR-006, FR-024, FR-025

## Purpose

Load, validate, and provide deployment configuration from `.env` file and command-line arguments.

## Interface

### Method: `load_configuration(db_path: str) -> DeploymentConfiguration`

**Description**: Load and validate deployment configuration

**Inputs**:
- `db_path`: str - Path to local SQLite database file (command-line arg)

**Outputs**:
- `DeploymentConfiguration` object (see data-model.md)

**Behavior**:
1. Load `.env` file using `python-dotenv`
2. Read `AZURE_REGION` from environment
3. Read optional settings (batch_size, validation_sample_pct, etc.)
4. Validate database file exists and is valid SQLite
5. Validate Azure region is valid
6. Auto-generate database and server names
7. Return populated configuration object

**Errors**:
- `DatabaseFileNotFoundException`: Database file not found (FR-002)
- `InvalidDatabaseException`: File is not valid SQLite database (FR-002)
- `ConfigurationMissingException`: Required .env settings missing (FR-025)
- `InvalidRegionException`: Region not in valid Azure regions (FR-024, FR-025)

**Requirements Mapping**:
- FR-001: Accept database file path
- FR-002: Validate database file
- FR-006: Read region from config file
- FR-024: Validate region
- FR-025: Clear error messages for config issues

---

### Method: `validate_database_file(db_path: str) -> ValidationResult`

**Description**: Check if file is valid SQLite database

**Inputs**:
- `db_path`: str - Path to database file

**Outputs**:
- `ValidationResult`:
  - `is_valid`: bool
  - `error_message`: Optional[str]
  - `file_size_mb`: float
  - `table_count`: int

**Behavior**:
- Check file exists
- Attempt to open with `sqlite3.connect()`
- Query `sqlite_master` to verify schema
- Get file size and table count

**Errors**:
- `DatabaseFileNotFoundException`: File not found
- `InvalidDatabaseException`: Not a valid SQLite database

**Requirements Mapping**:
- FR-002: Validate database file

---

### Method: `validate_region(region: str) -> bool`

**Description**: Check if region is valid Azure region

**Inputs**:
- `region`: str - Azure region name (e.g., "eastus")

**Outputs**:
- `bool` - True if valid, False otherwise

**Behavior**:
- Fetch list of valid regions from Azure SDK (optional: cache for performance)
- Compare input region against valid list (case-insensitive)

**Errors**: None (returns False for invalid regions)

**Requirements Mapping**:
- FR-024: Validate region is valid

---

### Method: `generate_database_name(db_path: str) -> str`

**Description**: Generate Azure SQL database name from local filename

**Inputs**:
- `db_path`: str - Path to local database

**Outputs**:
- `str` - Azure SQL database name (e.g., "oews-azure")

**Behavior**:
- Extract filename without extension (`Path(db_path).stem`)
- Sanitize: lowercase, replace non-alphanumeric with hyphens
- Append "-azure" suffix
- Truncate to 128 chars if needed (Azure SQL limit)

**Examples**:
- "oews.db" → "oews-azure"
- "My_Data_2024.sqlite" → "my-data-2024-azure"

**Requirements Mapping**:
- FR-007: Auto-generate database name from filename

---

## Contract Test Assertions

```python
def test_load_configuration_success():
    # Given: Valid .env and database file
    service = ConfigurationService()

    # When: Load configuration
    config = service.load_configuration("/path/to/oews.db")

    # Then: Configuration populated
    assert config.source_db_path == "/path/to/oews.db"
    assert config.azure_region == "eastus"  # from .env
    assert config.database_name == "oews-azure"

def test_load_configuration_missing_region():
    # Given: .env missing AZURE_REGION
    service = ConfigurationService()

    # When: Load configuration
    # Then: Raises exception with clear message
    with pytest.raises(ConfigurationMissingException) as exc:
        service.load_configuration("/path/to/oews.db")
    assert "AZURE_REGION" in str(exc.value)

def test_validate_database_file_not_found():
    # Given: Non-existent file path
    service = ConfigurationService()

    # When/Then: Raises exception
    with pytest.raises(DatabaseFileNotFoundException):
        service.validate_database_file("/nonexistent/path.db")

def test_validate_region_valid():
    # Given: Valid Azure region
    service = ConfigurationService()

    # When: Validate region
    result = service.validate_region("eastus")

    # Then: Returns True
    assert result == True

def test_validate_region_invalid():
    # Given: Invalid region
    service = ConfigurationService()

    # When: Validate region
    result = service.validate_region("invalid-region")

    # Then: Returns False
    assert result == False

def test_generate_database_name():
    # Given: Database file path
    service = ConfigurationService()

    # When: Generate name
    name = service.generate_database_name("/path/to/my_test.db")

    # Then: Name sanitized and suffixed
    assert name == "my-test-azure"
```
