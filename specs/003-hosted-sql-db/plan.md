# Implementation Plan: Azure SQL Database Deployment

**Branch**: `003-hosted-sql-db` | **Date**: 2025-10-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-hosted-sql-db/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → ✓ Feature spec loaded successfully
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → ✓ Python 3.10+ with Azure SDK, using existing project libraries
   → Project Type: single (CLI tool for Azure deployment)
3. Fill the Constitution Check section
   → ✓ Constitution check completed - PASS with documented deferrals
4. Evaluate Constitution Check section
   → ✓ No blocking violations, proceeding to research
5. Execute Phase 0 → research.md
   → ✓ Research complete - all technical decisions documented
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md
   → ✓ Data model complete (11 entities)
   → ✓ Service contracts generated (6 services)
   → ✓ Quickstart guide created with 6 test scenarios
   → ✓ CLAUDE.md updated with new technologies
7. Re-evaluate Constitution Check section
   → ✓ Post-design check - no new violations
8. Plan Phase 2 → Describe task generation approach
   → ✓ Task planning approach documented
9. STOP - Ready for /tasks command
   → ✓ Planning complete
```

## Summary

Deploy local SQLite database to Azure SQL Serverless with automated schema migration, data transfer, and consistency validation. System authenticates via Azure CLI, auto-generates cloud database names from local filenames, and performs automatic rollback on failures. Validation includes row count verification and 10% sample data integrity checks.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**:
- `azure-identity` (Azure CLI credential integration)
- `azure-mgmt-sql` (Azure SQL resource management)
- `pyodbc` or `pymssql` (Azure SQL connectivity)
- `sqlite3` (built-in, for reading local database)
- `python-dotenv` (configuration file management)
- `click` or `argparse` (CLI interface)
- Existing project libraries: `sqlalchemy`, `pandas` (for data operations)

**Storage**: SQLite (source) → Azure SQL Serverless (target)
**Testing**: pytest (existing project standard)
**Target Platform**: Cross-platform CLI (Windows/Linux/macOS)
**Project Type**: single (extends existing OEWS project structure)

**Performance Goals**:
- Progress updates every 5 seconds during migration
- Handle databases up to 5GB (initial target)
- Validation completes in <10 minutes for 1GB database

**Constraints**:
- Must use Azure CLI authentication (no credential management)
- Must preserve existing project structure and patterns
- Must follow constitution's testing and code quality standards
- Network-dependent operations (Azure API calls, data transfer)

**Scale/Scope**:
- Single SQLite database → single Azure SQL database migration
- Support for typical OEWS database size (100MB-5GB)
- CLI tool with progress reporting

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Code Quality Excellence
- ✅ **PASS**: Will use existing project patterns (black, flake8)
- ✅ **PASS**: Complex Azure operations will have comprehensive docstrings
- ✅ **PASS**: Code structure follows existing `src/` organization

### Principle II: Testing Standards
- ✅ **PASS**: TDD approach - contract tests before implementation
- ✅ **PASS**: Unit tests for schema conversion, validation logic
- ✅ **PASS**: Integration tests for Azure deployment flow
- ⚠️ **DEFER**: Performance tests - targets defined but depend on Azure environment setup

### Principle III: User Experience Consistency
- ✅ **PASS**: CLI progress indicators for operations >500ms
- ✅ **PASS**: Clear, actionable error messages (FR-019, FR-025)
- ✅ **PASS**: Consistent with existing CLI tools in `src/cli/`

### Principle IV: Performance Requirements
- ⚠️ **PARTIAL**: Database query performance not applicable (migration tool, not query service)
- ✅ **PASS**: Progress reporting requirement (FR-012) meets user feedback needs
- ⚠️ **DEFER**: Performance monitoring - deployment tool, not runtime service

### Principle V: Data Integrity
- ✅ **PASS**: Row count validation (FR-015)
- ✅ **PASS**: 10% sample hash verification (FR-016)
- ✅ **PASS**: Transaction rollback on failure (FR-020)
- ✅ **PASS**: Comprehensive logging (FR-021)

**Overall Assessment**: PASS with deferrals - Performance monitoring principles apply less to one-time deployment tool vs. runtime service. Core data integrity and quality principles fully satisfied.

## Project Structure

### Documentation (this feature)
```
specs/003-hosted-sql-db/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
src/
├── models/              # Existing - add Azure deployment models
├── services/            # Existing - add Azure migration services
├── cli/                 # Existing - add deploy command
│   ├── commands.py      # Extend with azure-deploy command
│   └── scripts/         # Add azure migration scripts
└── lib/                 # Existing - add Azure utilities
    ├── azure_client.py         # NEW: Azure SDK wrapper
    ├── schema_converter.py     # NEW: SQLite to Azure SQL schema mapping
    └── validation_engine.py    # NEW: Data consistency validation

tests/
├── contract/            # NEW: Azure API contract tests
├── integration/         # Existing - add deployment flow tests
└── unit/                # Existing - add converter/validator tests
```

**Structure Decision**: Single project structure - This feature extends the existing OEWS application with Azure deployment capability. New code will integrate into `src/services/` for core logic, `src/cli/` for user interface, and `src/lib/` for utilities, following established patterns from feature 002-i-want-to (data migration).

## Phase 0: Outline & Research
*Status: In Progress*

### Unknowns to Research

1. **Azure SQL Serverless Provisioning**
   - Research: Azure SDK patterns for creating serverless databases
   - Research: Resource group management and cleanup strategies
   - Research: Azure SQL authentication methods from Azure CLI credentials

2. **SQLite to Azure SQL Schema Mapping**
   - Research: Data type conversion matrix (SQLite → T-SQL)
   - Research: Constraint translation (CHECK, FOREIGN KEY handling)
   - Research: Index migration strategies

3. **Data Transfer Strategies**
   - Research: Bulk insert best practices for Azure SQL
   - Research: Batch size optimization for network transfer
   - Research: Progress tracking during large data transfers

4. **Error Handling & Rollback**
   - Research: Azure resource deletion patterns
   - Research: Partial migration cleanup strategies
   - Research: Transaction management across SQLite read + Azure SQL write

5. **Performance Targets**
   - Research: Typical Azure SQL Serverless provisioning time
   - Research: Expected throughput for data transfer (rows/second)
   - Research: Validation query performance on Azure SQL

### Research Task Generation

Generating research.md with findings for:
- Azure Python SDK (`azure-identity`, `azure-mgmt-sql`) usage patterns
- SQLite schema introspection techniques
- Azure SQL connection string construction from CLI credentials
- Batch insert performance optimization
- Naming collision handling strategies

**Next Step**: Create research.md with consolidated findings

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

**Planned Activities**:

1. **Extract entities from spec** → `data-model.md`:
   - MigrationJob (tracks deployment state)
   - SchemaDefinition (SQLite → Azure SQL mapping)
   - ValidationReport (consistency check results)
   - ConfigurationSettings (region, resource group)

2. **Generate service contracts** → `/contracts/`:
   - AzureAuthenticationService (verify CLI session)
   - AzureProvisioningService (create database)
   - SchemaMigrationService (convert and apply schema)
   - DataTransferService (bulk copy data)
   - ValidationService (row counts + sample hashing)
   - RollbackService (cleanup on failure)

3. **Generate contract tests** → `tests/contract/`:
   - Test files for each service contract
   - Mock Azure SDK responses
   - Assert expected behavior per FR requirements

4. **Extract test scenarios** from user stories → integration tests:
   - Scenario 1: Successful full migration
   - Scenario 2: Invalid database path handling
   - Scenario 3: Missing Azure CLI session
   - Scenario 4: Invalid region configuration
   - Scenario 5: Validation failure detection
   - Scenario 6: Automatic rollback on failure

5. **Update CLAUDE.md** incrementally with new technologies

**Output**: data-model.md, /contracts/*, failing contract tests, quickstart.md, CLAUDE.md update

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs in TDD order
- Each service contract → contract test task [P] (can run parallel)
- Each model → model implementation task [P]
- Schema converter → conversion logic + unit tests
- Integration tests for end-to-end flows (sequential - depend on services)
- CLI interface implementation (depends on services)

**Ordering Strategy**:
1. Contract tests (parallel, all fail initially)
2. Model implementations (parallel, support contracts)
3. Service implementations (make contract tests pass):
   - Azure authentication service
   - Configuration service
   - Schema converter service
   - Provisioning service
   - Data transfer service
   - Validation service
   - Rollback service
4. Integration tests (sequential, verify end-to-end flows)
5. CLI command implementation
6. Quickstart validation

**Estimated Output**: 30-35 tasks in dependency order with [P] markers for parallelizable work

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, validate against FR requirements)

## Complexity Tracking

*No constitutional violations requiring justification*

## Progress Tracking

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [x] Phase 3: Tasks generated (/tasks command) - 41 tasks in TDD order
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS (with documented deferrals)
- [x] Post-Design Constitution Check: PASS (no new violations)
- [x] All NEEDS CLARIFICATION resolved: Complete (research.md)
- [x] Complexity deviations documented: N/A (no violations)

---
*Based on Constitution v1.0.0 - See `.specify/memory/constitution.md`*
