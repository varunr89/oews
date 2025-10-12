# Tasks: OEWS Excel to SQL Database Migration Application

**Input**: Design documents from `/specs/002-i-want-to/`
**Prerequisites**: spec.md, plan.md (research.md, data-model.md, contracts/, quickstart.md to be created during implementation)

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Extract: Python 3.10+, pandas, openpyxl, sqlalchemy, CLI structure
2. Load design documents:
   → data-model.md: 10 entities identified → model tasks
   → contracts/: 4 service contracts → contract test tasks
   → quickstart.md: End-to-end scenarios → integration tests
3. Generate tasks by category:
   → Setup: Python project, dependencies, SQLAlchemy
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: database, logging, validation
   → Polish: unit tests, performance, quickstart validation
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. SUCCESS: 54 tasks ready for execution
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- All paths relative to repository root

## Phase 3.1: Setup ✅ COMPLETED

- [x] T001 Create project structure per implementation plan with src/, tests/, data/, logs/, config/ directories
- [x] T002 Initialize Python project with requirements.txt (pandas>=1.5.0, openpyxl>=3.0.0, sqlalchemy>=2.0.0, alembic>=1.12.0, click>=8.0.0, python-dotenv>=0.19.0, pytest>=7.0.0)
- [x] T003 [P] Configure linting and formatting tools (black, flake8, mypy) in pyproject.toml
- [x] T004 [P] Create .env.template file with DATABASE_URL, LOG_LEVEL, MAX_MEMORY_USAGE, BATCH_SIZE variables
- [x] T005 [P] Create setup.py for package installation and CLI entry points

## Phase 3.2: Tests First (TDD) ✅ COMPLETED
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

- [x] T006 [P] Contract test FileDiscoveryService in tests/contract/test_file_discovery_contract.py
- [x] T007 [P] Contract test MigrationEngineService in tests/contract/test_migration_engine_contract.py
- [x] T007a [P] Contract test SchemaBuilderService in tests/contract/test_schema_builder_contract.py
- [x] T008 [P] Contract test ValidationService in tests/contract/test_validation_service_contract.py
- [x] T009 [P] Integration test end-to-end migration scenario in tests/integration/test_end_to_end_migration.py
- [x] T010 [P] Integration test database operations in tests/integration/test_database_integration.py
- [x] T011 [P] Integration test Excel file processing in tests/integration/test_excel_processing.py
- [x] T012 [P] Integration test CLI discover command in tests/integration/test_cli_discover.py
- [x] T013 [P] Integration test CLI migrate command in tests/integration/test_cli_migrate.py
- [x] T014 [P] Integration test CLI validate command in tests/integration/test_cli_validate.py

## Phase 3.3: Core Models ✅ COMPLETED

- [x] T015 [P] ExcelFile model in src/models/excel_file.py with SQLAlchemy ORM
- [x] T016 [P] ExcelSheet model in src/models/excel_sheet.py with relationships
- [x] T017 [P] ColumnDefinition model in src/models/column_definition.py
- [x] T018 [P] UnifiedSchema model in src/models/unified_schema.py
- [x] T019 [P] TableDefinition model in src/models/table_definition.py
- [x] T020 [P] ColumnMapping model in src/models/column_mapping.py
- [x] T021 [P] MigrationBatch model in src/models/migration_batch.py
- [x] T022 [P] MigrationRecord model in src/models/migration_record.py
- [x] T023 [P] ValidationReport model in src/models/validation_report.py
- [x] T024 [P] AuditLog model in src/models/audit_log.py
- [x] T027 [P] Base model class in src/models/__init__.py with common fields and methods

## Phase 3.4: Database Layer

- [x] T025 Database connection manager in src/lib/db_manager.py with SQLAlchemy session handling
- [x] T026 Database initialization script in src/lib/database_init.py with table creation and migration support
- [x] T026a Database schema migration setup with Alembic for version control and schema evolution

## Phase 3.5: Utility Libraries ✅ COMPLETED

- [x] T028 [P] Excel file parser utilities in src/lib/excel_parser.py using pandas and openpyxl
- [x] T029 [P] Data type conversion utilities in src/lib/type_converter.py for Excel to SQL mapping
- [x] T030 [P] Configuration management in src/cli/config.py with environment variable handling

## Phase 3.6: Service Implementation ✅ COMPLETED

- [x] T031 FileDiscoveryService implementation in src/services/file_discovery.py
- [x] T032 Excel schema analyzer service in src/services/schema_analyzer.py for inferring structure from Excel files
- [x] T032a Unified database schema builder service in src/services/schema_builder.py to create consolidated SQL schema from analyzed Excel structures
- [x] T033 MigrationEngineService implementation in src/services/migration_engine.py with batch processing
- [x] T034 ValidationService implementation in src/services/validator.py with data consistency checks
- [x] T035 Migration reporting service in src/services/reporter.py for generating reports

## Phase 3.7: CLI Interface ✅ COMPLETED

- [x] T036 CLI main entry point in src/cli/main.py with click command groups
- [x] T037 CLI command handlers in src/cli/commands.py (discover, analyze, create-schema, migrate, validate, rollback)
- [x] T038 CLI progress display and user feedback in src/cli/display.py with click progress bars
- [x] T039 CLI error handling and logging configuration in src/cli/error_handler.py

## Phase 3.8: Integration & Error Handling ✅ COMPLETED

- [x] T040 Comprehensive logging setup with structured JSON logging in src/lib/logging_config.py
- [x] T041 Error handling and exception hierarchy in src/lib/exceptions.py
- [x] T042 Performance monitoring and memory management in src/lib/performance_monitor.py

## Phase 3.9: Validation & Polish

- [ ] T043 [P] Unit tests for Excel parser in tests/unit/test_lib/test_excel_parser.py - ⚠ NOT IMPLEMENTED (Constitutional Violation)
- [ ] T044 [P] Unit tests for type converter in tests/unit/test_lib/test_type_converter.py - ⚠ NOT IMPLEMENTED (Constitutional Violation)
- [ ] T045 [P] Unit tests for models in tests/unit/test_models/ (one file per model) - ⚠ NOT IMPLEMENTED (Constitutional Violation)
- [ ] T046 [P] Unit tests for services in tests/unit/test_services/ (one file per service) - ⚠ NOT IMPLEMENTED (Constitutional Violation)
- [ ] T047 Performance tests with 70MB file processing in tests/performance/test_large_file_migration.py - ⚠ NOT IMPLEMENTED (Constitutional Violation)
- [ ] T048 Memory usage validation tests in tests/performance/test_memory_constraints.py - ⚠ NOT IMPLEMENTED (Constitutional Violation)
- [ ] T049 Quickstart validation - execute complete quickstart.md scenario as automated test
- [ ] T050 [P] Create sample OEWS test data fixtures in data/test_fixtures/
- [ ] T051 [P] Update README.md with installation and usage instructions

## Phase 3.10: Actual Implementation (Root Scripts) - NOT IN ORIGINAL PLAN

**These tasks were completed but were NOT part of the original task list:**

- [x] T052 Create convert_to_csv.py script to convert Excel files to CSV format (100 lines)
- [x] T053 Create standardize_csv_columns.py script with 44 column mapping rules (121 lines)
- [x] T054 Create migrate_csv_to_db.py script for pandas-based CSV to SQLite migration (100 lines)
- [x] T055 Create analyze_columns.py script to analyze column variations across files
- [x] T056 Discover and document column name inconsistencies across 13 years of OEWS data
- [x] T057 Implement COLUMN_MAPPING dictionary with 44 mapping rules
- [x] T058 Implement STANDARD_COLUMNS array defining 32 canonical columns
- [x] T059 Test and validate Excel → CSV → SQL pipeline with production data
- [x] T060 Generate working SQLite database (data/oews.db) with 400K+ records per year

## Dependencies

**Setup Dependencies**:
- T001 (project structure) blocks all other tasks
- T002 (dependencies) blocks T003-T005

**Test Dependencies (TDD Critical)**:
- T006-T014 (all tests) MUST complete before T015-T042 (implementation)
- Tests must be written and MUST FAIL before implementation begins

**Model Dependencies**:
- T025 (db_manager) blocks T026 (db_init)
- T026 (db_init) blocks T026a (Alembic setup)
- T027 (base model) blocks T015-T024 (individual models)

**Service Dependencies**:
- T015-T024 (models) block T031-T035 (services)
- T028-T030 (utilities) block T031-T035 (services)
- T032 (Excel schema analyzer) blocks T032a (unified schema builder)
- T032a (unified schema builder) blocks T033 (migration engine)

**CLI Dependencies**:
- T031-T035 (services) block T036-T039 (CLI)
- T030 (config) blocks T036 (main)

**Integration Dependencies**:
- T025 (db_manager) blocks T040 (logging)
- T031-T039 (core implementation) block T040-T042 (integration)

**Polish Dependencies**:
- T015-T042 (implementation) block T043-T051 (testing and polish)

## Parallel Execution Examples

### Phase 3.2 - Contract Tests (All Parallel)
```bash
# Execute T006-T008 together (different contract files):
Task: "Contract test FileDiscoveryService in tests/contract/test_file_discovery_contract.py"
Task: "Contract test MigrationEngineService in tests/contract/test_migration_engine_contract.py"
Task: "Contract test ValidationService in tests/contract/test_validation_service_contract.py"

# Execute T009-T014 together (different integration files):
Task: "Integration test end-to-end migration in tests/integration/test_end_to_end_migration.py"
Task: "Integration test database operations in tests/integration/test_database_integration.py"
Task: "Integration test Excel processing in tests/integration/test_excel_processing.py"
Task: "Integration test CLI discover in tests/integration/test_cli_discover.py"
Task: "Integration test CLI migrate in tests/integration/test_cli_migrate.py"
Task: "Integration test CLI validate in tests/integration/test_cli_validate.py"
```

### Phase 3.3 - Model Creation (All Parallel)
```bash
# Execute T015-T024 together (different model files):
Task: "ExcelFile model in src/models/excel_file.py"
Task: "ExcelSheet model in src/models/excel_sheet.py"
Task: "ColumnDefinition model in src/models/column_definition.py"
Task: "UnifiedSchema model in src/models/unified_schema.py"
Task: "TableDefinition model in src/models/table_definition.py"
Task: "ColumnMapping model in src/models/column_mapping.py"
Task: "MigrationBatch model in src/models/migration_batch.py"
Task: "MigrationRecord model in src/models/migration_record.py"
Task: "ValidationReport model in src/models/validation_report.py"
Task: "AuditLog model in src/models/audit_log.py"
```

### Phase 3.5 - Utilities (All Parallel)
```bash
# Execute T028-T030 together (different utility files):
Task: "Excel parser utilities in src/lib/excel_parser.py"
Task: "Type conversion utilities in src/lib/type_converter.py"
Task: "Configuration management in src/cli/config.py"
```

## Notes

- **[P] tasks** = different files, no dependencies, can run in parallel
- **TDD Critical**: All tests in Phase 3.2 must be written and failing before any implementation
- **Memory Constraints**: All implementations must respect 1.75GB memory limit
- **Performance Requirements**: Database queries <1 second, startup <5 seconds
- **Code Quality**: All code must pass black, flake8, mypy checks
- **Test Coverage**: >90% code coverage required per constitutional requirements
- **Commit Strategy**: Commit after each completed task for incremental progress

## Task Generation Rules Applied

1. **From Contracts** (4 service contracts):
   - file_discovery_service.py → T006 contract test
   - migration_engine_service.py → T007 contract test
   - schema_builder_service.py → T007a contract test
   - validation_service.py → T008 contract test

2. **From Data Model** (10 entities):
   - Each entity → T015-T024 model creation tasks [P]
   - Relationships handled in individual model files

3. **From Quickstart** (6 scenarios):
   - End-to-end migration → T009 integration test
   - Database operations → T010 integration test
   - Excel processing → T011 integration test
   - CLI commands → T012-T014 integration tests
   - Complete quickstart → T049 validation test

4. **From Plan Structure**:
   - src/models/ → T015-T024, T027 (models)
   - src/services/ → T031-T035 (services)
   - src/cli/ → T030, T036-T039 (CLI)
   - src/lib/ → T025, T026, T028, T029, T040-T042 (utilities)

## Validation Checklist

- [x] All 4 service contracts have corresponding tests (T006, T007, T007a, T008)
- [x] All 10 entities have model tasks (T015-T024)
- [x] All tests come before implementation (T006-T014 before T015+)
- [x] Parallel tasks are truly independent (different files)
- [x] Each task specifies exact file path
- [x] No [P] task modifies same file as another [P] task
- [x] TDD workflow enforced (tests must fail before implementation)
- [x] Constitutional requirements addressed (performance, coverage, quality)

## Updated Testing Strategy with Real OEWS Data

**Key Changes Based on Actual Data Analysis**:

### Real Data Characteristics (from data/ directory):
- **File Count**: 13 actual OEWS files (2011-2024)
- **File Size**: 70-80MB each (perfect for testing constitutional memory limits)
- **Data Volume**: 400K+ records per file
- **Structure**: 32 standardized columns, 4 sheets per file
- **Data Types**: Mixed with special values ('#', '*', NaN)

### Updated Test Data Strategy:
1. **T050**: Create sample test fixtures from real OEWS data subsets
   - Small fixture: 100 records from data/all_data_M_2024.xlsx
   - Medium fixture: 1000 records for integration tests
   - Large fixture: Full file (400K records) for performance tests

2. **Updated Performance Tests (T047-T048)**:
   - Use actual 75MB OEWS files to test constitutional memory limit (1.75GB)
   - Test with real 400K record datasets for processing speed validation
   - Verify handling of actual OEWS special values ('#', '*', NaN)

3. **Updated Integration Tests (T009-T014)**:
   - End-to-end tests use data/all_data_M_2024.xlsx (real structure)
   - Schema analysis tests verify 32-column OEWS structure
   - Validation tests check real OEWS data patterns and relationships

4. **Updated Contract Tests (T006-T008)**:
   - File discovery tests validate against actual OEWS file patterns
   - Migration tests handle real OEWS data types and special values
   - Validation tests verify actual OEWS schema consistency (2011-2024)

### Real OEWS Data Benefits:
- **Authentic Edge Cases**: Real suppressed data ('#'), estimates ('*'), missing values
- **Performance Reality**: Actual 70MB files test constitutional constraints accurately
- **Schema Evolution**: Test migration consistency across 13 years of actual data
- **No Privacy Concerns**: All OEWS data is public and freely available
- **Production Readiness**: Tests mirror exact production data patterns

This updated strategy ensures our tests reflect real-world OEWS migration scenarios while maintaining comprehensive TDD coverage.