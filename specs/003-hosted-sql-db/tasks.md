# Tasks: Azure SQL Database Deployment

**Feature**: 003-hosted-sql-db
**Input**: Design documents from `/specs/003-hosted-sql-db/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/, quickstart.md

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → ✓ Tech stack: Python 3.10+, Azure SDK, pyodbc/pymssql
   → ✓ Structure: Single project (src/, tests/)
2. Load optional design documents:
   → ✓ data-model.md: 11 entities extracted
   → ✓ contracts/: 6 service contracts found
   → ✓ research.md: Technical decisions loaded
   → ✓ quickstart.md: 6 test scenarios extracted
3. Generate tasks by category: In progress
4. Apply task rules: TDD order, parallel markers
5. Number tasks sequentially: T001-T041
6. Generate dependency graph: Complete
7. Create parallel execution examples: Complete
8. Validate task completeness: All contracts/entities covered
9. Return: SUCCESS (41 tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
Single project structure (from plan.md):
- Implementation: `src/models/`, `src/services/`, `src/lib/`, `src/cli/`
- Tests: `tests/contract/`, `tests/integration/`, `tests/unit/`

---

## Phase 3.1: Setup & Dependencies

- [ ] **T001** Install Azure SDK dependencies: Add `azure-identity==1.15.0`, `azure-mgmt-sql==4.0.0`, `azure-mgmt-resource==23.0.0`, `pyodbc>=5.0.0`, `pymssql>=2.2.0` to `requirements.txt`

- [ ] **T002** [P] Create directory structure: `src/lib/`, `tests/contract/`, `tests/integration/`, `tests/unit/test_azure/`

- [ ] **T003** [P] Configure pytest fixtures in `tests/conftest.py`: Add fixtures for mock Azure clients, SQLite test databases, mock connections

---

## Phase 3.2: Contract Tests (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Service Contract Tests (All Parallel)

- [ ] **T004** [P] Contract test for AzureAuthenticationService in `tests/contract/test_authentication_service.py`: Test `verify_cli_session()`, `get_credential()`, `validate_permissions()` with mocked Azure CLI responses

- [ ] **T005** [P] Contract test for ConfigurationService in `tests/contract/test_configuration_service.py`: Test `load_configuration()`, `validate_database_file()`, `validate_region()`, `generate_database_name()` with test fixtures

- [ ] **T006** [P] Contract test for AzureProvisioningService in `tests/contract/test_provisioning_service.py`: Test `create_resource_group()`, `create_sql_server()`, `create_sql_database()`, `delete_resources()` with mocked Azure SDK

- [ ] **T007** [P] Contract test for SchemaMigrationService in `tests/contract/test_schema_migration_service.py`: Test `extract_schema()`, `convert_schema()`, `apply_schema()`, `get_table_creation_order()` with sample SQLite database

- [ ] **T008** [P] Contract test for DataTransferService in `tests/contract/test_data_transfer_service.py`: Test `transfer_table()`, `transfer_all_tables()`, `build_insert_statement()` with test data

- [ ] **T009** [P] Contract test for ValidationService in `tests/contract/test_validation_service.py`: Test `validate_migration()`, `validate_row_counts()`, `validate_sample_hash()`, `generate_validation_report()` with matching/mismatched test databases

### Integration Test Scenarios (All Parallel)

- [ ] **T010** [P] Integration test for successful migration scenario in `tests/integration/test_full_migration.py`: Implement quickstart Scenario 1 - mock Azure resources, verify all steps complete

- [ ] **T011** [P] Integration test for invalid database path in `tests/integration/test_error_handling.py`: Implement quickstart Scenario 2 - verify error message and exit code

- [ ] **T012** [P] Integration test for missing Azure CLI session in `tests/integration/test_authentication_errors.py`: Implement quickstart Scenario 3 - verify authentication failure handling

- [ ] **T013** [P] Integration test for invalid region configuration in `tests/integration/test_configuration_errors.py`: Implement quickstart Scenario 4 - verify configuration validation

- [ ] **T014** [P] Integration test for validation failure detection in `tests/integration/test_validation_failures.py`: Implement quickstart Scenario 6 - verify validation report generation with failures

- [ ] **T015** [P] Integration test for rollback on failure in `tests/integration/test_rollback.py`: Implement quickstart Scenario 5 - verify automatic rollback deletes all resources

---

## Phase 3.3: Data Models (All Parallel - Different Files)

- [ ] **T016** [P] DeploymentConfiguration model in `src/models/deployment_configuration.py`: Implement with validation rules, from_env() classmethod

- [ ] **T017** [P] SchemaDefinition and column models in `src/models/schema_definition.py`: Implement SchemaDefinition, ColumnDefinition, ForeignKeyConstraint, IndexDefinition, CheckConstraint with to_tsql() methods

- [ ] **T018** [P] MigrationJob model in `src/models/migration_job.py`: Implement with MigrationStatus enum, state tracking, progress methods, to_dict() serialization

- [ ] **T019** [P] AzureResource model in `src/models/azure_resource.py`: Implement resource tracking for rollback with delete() method

- [ ] **T020** [P] ValidationReport models in `src/models/validation_report.py`: Implement ValidationReport, TableValidationResult, ValidationStatus enum, to_json() export

- [ ] **T021** [P] ProgressEvent model in `src/models/progress_event.py`: Implement real-time progress tracking with format_message() method

---

## Phase 3.4: Core Services (Sequential - Dependencies)

### Utility Services (Parallel)

- [ ] **T022** [P] Azure client wrapper in `src/lib/azure_client.py`: Implement AzureCliCredential wrapper, connection string builder, credential validation

- [ ] **T023** [P] Schema type converter in `src/lib/schema_converter.py`: Implement SQLite to T-SQL type mapping table, data type conversion functions

- [ ] **T024** [P] Validation hash engine in `src/lib/validation_engine.py`: Implement row sampling, SHA256 hashing, comparison logic

### Service Implementations (Make Contract Tests Pass)

- [ ] **T025** ConfigurationService implementation in `src/services/configuration_service.py`: Implement load_configuration(), validate_database_file(), validate_region(), generate_database_name() - makes T005 pass

- [ ] **T026** AzureAuthenticationService implementation in `src/services/authentication_service.py`: Implement verify_cli_session(), get_credential(), validate_permissions() using azure-identity - makes T004 pass

- [ ] **T027** SchemaMigrationService implementation in `src/services/schema_migration_service.py`: Implement extract_schema() with PRAGMA queries, convert_schema() with type mapping, apply_schema() with dependency ordering - makes T007 pass

- [ ] **T028** AzureProvisioningService implementation in `src/services/provisioning_service.py`: Implement create_resource_group(), create_sql_server(), create_sql_database(), delete_resources() using azure-mgmt-sql - makes T006 pass

- [ ] **T029** DataTransferService implementation in `src/services/data_transfer_service.py`: Implement transfer_table() with batch inserts, transfer_all_tables() with progress callbacks, build_insert_statement() - makes T008 pass

- [ ] **T030** ValidationService implementation in `src/services/validation_service.py`: Implement validate_migration(), validate_row_counts(), validate_sample_hash(), generate_validation_report() - makes T009 pass

---

## Phase 3.5: Orchestration & CLI

- [ ] **T031** DeploymentOrchestrator in `src/services/deployment_orchestrator.py`: Implement main deployment workflow coordinating all services, state machine, error handling, rollback logic

- [ ] **T032** CLI deploy command in `src/cli/commands.py`: Add `deploy-azure` command using click, argument parsing, progress display, error formatting

- [ ] **T033** Progress reporter in `src/lib/progress_reporter.py`: Implement console progress display with spinner, percentage, ETA calculation

- [ ] **T034** Logging configuration in `src/lib/azure_logging.py`: Configure deployment logging to file, structured log format, sensitive data filtering (SR-001)

---

## Phase 3.6: Unit Tests & Polish

- [ ] **T035** [P] Unit tests for schema converter in `tests/unit/test_azure/test_schema_converter.py`: Test all SQLite→T-SQL type mappings, edge cases, constraint translations

- [ ] **T036** [P] Unit tests for validation engine in `tests/unit/test_azure/test_validation_engine.py`: Test sampling logic, hash generation, comparison functions

- [ ] **T037** [P] Unit tests for name generation in `tests/unit/test_azure/test_name_generation.py`: Test database/server name sanitization, collision handling

- [ ] **T038** Performance validation: Run quickstart.md with 1GB test database, verify meets performance targets (provisioning <8min, transfer 5-10k rows/sec, validation <10min)

- [ ] **T039** Security audit: Review code for SR-001 (no credential logging), SR-002 (secure credential handling), SR-003 (permission validation)

- [ ] **T040** Code quality check: Run `black src/ tests/`, `flake8 src/ tests/`, fix all violations per constitution

- [ ] **T041** Documentation: Update README.md with Azure deployment section, quickstart usage examples, troubleshooting guide

---

## Dependencies

### Critical Ordering
1. **Setup (T001-T003)** must complete before all other phases
2. **Contract Tests (T004-T015)** MUST complete and FAIL before implementation
3. **Models (T016-T021)** must complete before services that use them
4. **Services (T022-T030)** must pass their contract tests before orchestration
5. **Orchestration (T031)** depends on all services
6. **CLI (T032)** depends on orchestrator
7. **Polish (T035-T041)** after all implementation complete

### Specific Dependencies
- T025 (ConfigurationService) blocks T031 (needs config loading)
- T026 (AuthService) blocks T028 (provisioning needs auth)
- T027 (SchemaMigration) blocks T031 (orchestrator needs schema converter)
- T028 (Provisioning) blocks T029, T030 (need Azure resources)
- T029 (DataTransfer) blocks T030 (validation needs data)
- T031 (Orchestrator) blocks T032 (CLI wraps orchestrator)

---

## Parallel Execution Examples

### Phase 3.2: All Contract Tests Together
```bash
# Launch T004-T009 simultaneously (6 parallel tasks)
# Each tests a different service in different file
pytest tests/contract/ -n 6
```

### Phase 3.2: All Integration Tests Together
```bash
# Launch T010-T015 simultaneously (6 parallel tasks)
pytest tests/integration/ -n 6
```

### Phase 3.3: All Models Together
```bash
# Launch T016-T021 simultaneously (6 parallel tasks)
# Each creates a different model file
Task: "Create DeploymentConfiguration model in src/models/deployment_configuration.py"
Task: "Create SchemaDefinition models in src/models/schema_definition.py"
Task: "Create MigrationJob model in src/models/migration_job.py"
Task: "Create AzureResource model in src/models/azure_resource.py"
Task: "Create ValidationReport models in src/models/validation_report.py"
Task: "Create ProgressEvent model in src/models/progress_event.py"
```

### Phase 3.4: Utility Services in Parallel
```bash
# Launch T022-T024 simultaneously (3 parallel tasks)
Task: "Implement azure_client wrapper in src/lib/azure_client.py"
Task: "Implement schema converter in src/lib/schema_converter.py"
Task: "Implement validation engine in src/lib/validation_engine.py"
```

### Phase 3.6: Unit Tests in Parallel
```bash
# Launch T035-T037 simultaneously (3 parallel tasks)
pytest tests/unit/test_azure/ -n 3
```

---

## Validation Checklist
*GATE: All items must be checked before feature complete*

- [x] All 6 contracts have corresponding tests (T004-T009)
- [x] All 11 entities have model tasks (T016-T021 covers key entities)
- [x] All tests come before implementation (T004-T015 before T016-T041)
- [x] Parallel tasks truly independent (same-file conflicts avoided)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] All 6 quickstart scenarios have integration tests (T010-T015)
- [x] TDD order maintained (tests fail before implementation)

---

## Notes

### Test-First Approach
- **CRITICAL**: T004-T015 must be written first and must FAIL
- Do NOT proceed to T016 until all contract tests are failing
- Each service implementation task (T025-T030) should make specific tests pass

### Parallel Execution
- [P] tasks operate on different files with no shared state
- Can be executed simultaneously for faster development
- Example: All 6 contract tests can run at once (T004-T009)

### File Organization
```
src/
├── models/              # T016-T021 (6 files)
├── services/            # T025-T031 (7 files)
├── lib/                 # T022-T024, T033-T034 (5 files)
└── cli/                 # T032 (extend existing)

tests/
├── contract/            # T004-T009 (6 files)
├── integration/         # T010-T015 (6 files)
└── unit/test_azure/     # T035-T037 (3 files)
```

### Commit Strategy
- Commit after each completed task
- Commit message format: `feat(azure): [Task ID] - description`
- Example: `feat(azure): T004 - Add contract test for authentication service`

### Constitution Compliance
- T040: Verify code quality (black, flake8) per Principle I
- All tests: Support Principle II (TDD, >90% coverage)
- T032-T033: Implement Principle III (progress indicators, clear errors)
- T038: Validate Principle IV (performance targets)
- T029-T030: Ensure Principle V (data integrity validation)

---

**Status**: Task list complete - 41 tasks ready for execution in TDD order
**Estimated Effort**: 35-40 hours (5-6 days with parallelization)
**Next**: Execute tasks in order, marking complete as you go
