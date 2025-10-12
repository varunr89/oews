
# Implementation Plan: OEWS Excel to SQL Database Migration Application

**Branch**: `002-i-want-to` | **Date**: 2025-10-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-i-want-to/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Data migration application to consolidate historical OEWS (Occupational Employment and Wage Statistics) Excel files into a centralized SQL database. The system performs file discovery, schema analysis, unified database schema creation, data migration with type conversion, duplicate handling, and comprehensive validation. Key features include per-file rollback capability, incremental migration support, and data consistency verification. System targets 10 years of data (~700MB total) with robust error handling and audit logging.

## Implementation Reality (Added 2025-10-11)

**CRITICAL UPDATE**: The actual implementation diverged from the planned architecture:

**Planned Architecture**: Direct Excel → SQL migration using service-oriented architecture
**Actual Implementation**: Excel → CSV → Column Standardization → SQL using root-level scripts

### Dual Implementation Approach
1. **Production Workflow** (Root Scripts - Currently Used):
   - `convert_to_csv.py` - Converts Excel to CSV (100 lines)
   - `standardize_csv_columns.py` - Normalizes 44 column name variants (121 lines)
   - `migrate_csv_to_db.py` - Loads CSV into SQLite using pandas (100 lines)
   - **Rationale**: 10-20x faster, debuggable intermediate files, working production database

2. **Service Architecture** (Fully Implemented - Alternative):
   - `src/services/` - All planned services implemented (file_discovery, schema_analyzer, schema_builder, migration_engine, validator, reporter)
   - `src/cli/` - Full CLI with commands (discover, analyze, create-schema, migrate, validate, rollback)
   - `src/models/` - All 10 SQLAlchemy models implemented
   - **Status**: Complete but not used in primary workflow

### Key Discovery: Column Standardization Required
Original spec did not account for column name inconsistencies across 13 years of OEWS data:
- 44 column mapping rules (e.g., 'occ code' → 'OCC_CODE', 'group' → 'O_GROUP')
- 32 standardized columns in final schema
- Special handling for variants, abbreviations, and semantic differences

### Folder Structure Deviations
**Extra directories not in plan**:
- `config/` - Configuration files (duplicates `src/cli/config.py`)
- `notebook/` - Jupyter notebook utilities
- `migrations/` - Empty (Alembic used instead)
- `src/database/` - Database utilities (overlaps with `src/lib/db_manager.py`)

**Missing implementations**:
- Unit tests: 0 files (constitutional requirement: >90% coverage)
- Performance tests: 0 files (planned in tasks.md T047-T048)
- `data/schemas/` directory (not created)

## Technical Context
**Language/Version**: Python 3.10+ (per constitution requirements)
**Primary Dependencies**: pandas, openpyxl, sqlalchemy, sqlite3/postgresql
**Storage**: SQL database (SQLite for development, PostgreSQL for production)
**Testing**: pytest with >90% code coverage (per constitution)
**Target Platform**: Cross-platform CLI application (Windows, Linux, macOS)
**Project Type**: single - command-line data migration tool
**Performance Goals**: <1 second for database queries, <5 second startup time (per constitution)
**Constraints**: <1.75GB memory usage, transactional rollback capability
**Scale/Scope**: 10 years of OEWS data (~700MB), up to 70MB per annual file

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Code Quality Excellence**: ✅ PASS
- Python 3.10+ with black, flake8 enforcement planned
- Docstrings required for complex functions (schema analysis, migration logic)
- Code review process will verify readability and maintainability

**Testing Standards**: ✅ PASS
- TDD approach with tests before implementation
- >90% code coverage requirement
- Unit tests for all migration components, integration tests for database operations
- Performance tests for data volume requirements

**Data Integrity**: ✅ PASS
- SQLAlchemy ORM with referential integrity constraints
- Transaction rollback on validation failures
- Comprehensive logging with timestamp and source tracking
- Data accuracy validation against source Excel files

**Performance Requirements**: ✅ PASS
- Database queries <1 second target
- Application startup <5 seconds
- Memory usage within 1.75GB limit
- Caching for expensive schema analysis operations

**Technical Standards**: ✅ PASS
- Python 3.10+ per constitution
- SQLAlchemy ORM with connection pooling
- Environment variable configuration
- Conventional commit messages and semantic versioning

**Post-Design Re-evaluation**: ✅ PASS
- Service-oriented architecture maintains code quality standards
- Contract-based design enables comprehensive testing
- Data model supports all constitutional data integrity requirements
- CLI interface provides consistent user experience
- Validation framework ensures performance requirements are met

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
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
├── models/
│   ├── excel_file.py          # OEWS Excel file entity
│   ├── migration_record.py    # Migration tracking entity
│   └── schema.py              # Unified database schema entity
├── services/
│   ├── file_discovery.py      # Excel file enumeration service
│   ├── schema_analyzer.py     # Excel schema analysis service
│   ├── schema_builder.py      # Unified database schema builder service
│   ├── migration_engine.py    # Core migration logic service
│   ├── validator.py           # Data consistency validation service
│   └── reporter.py            # Migration reporting service
├── cli/
│   ├── main.py                # CLI entry point
│   ├── commands.py            # Command handlers
│   └── config.py              # Configuration management
└── lib/
    ├── excel_parser.py        # Excel file parsing utilities
    ├── type_converter.py      # Data type conversion utilities
    └── db_manager.py          # Database connection and transaction utilities

tests/
├── contract/
│   ├── test_file_discovery_contract.py
│   ├── test_migration_engine_contract.py
│   ├── test_schema_builder_contract.py
│   └── test_validator_contract.py
├── integration/
│   ├── test_end_to_end_migration.py
│   ├── test_database_integration.py
│   └── test_excel_processing.py
└── unit/
    ├── test_models/
    ├── test_services/
    ├── test_cli/
    └── test_lib/

data/
├── test_fixtures/             # Sample OEWS Excel files for testing
└── schemas/                   # SQL schema definitions

logs/                          # Migration logs and reports
config/                        # Configuration files
requirements.txt               # Python dependencies
setup.py                       # Package setup
README.md                      # Project documentation
```

**Structure Decision**: Single project layout chosen as this is a command-line data migration tool without web frontend or mobile components. The structure separates concerns with clear layers: models for data entities, services for business logic, CLI for user interface, and lib for shared utilities.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType claude`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each service contract → contract test task [P] (file_discovery, schema_builder, migration_engine, validation)
- Each data model entity → SQLAlchemy model creation task [P]
- Each CLI command → integration test task
- Implementation tasks following TDD approach to make tests pass
- Validation tasks for quickstart scenarios

**Ordering Strategy**:
1. **Foundation Layer** [P]: Core models and database setup
2. **Service Layer Tests** [P]: Contract tests for all services
3. **Service Implementation**: File discovery → Schema analysis → Schema building → Migration engine → Validation
4. **CLI Layer**: Command handlers and user interface
5. **Integration Tests**: End-to-end migration scenarios
6. **Performance Validation**: Memory, speed, and volume testing

**Parallel Execution Groups**:
- [P1]: Model creation tasks (all entities independent)
- [P2]: Contract test creation (services independent)
- [P3]: Utility library implementation (independent components)
- [P4]: Integration test scenarios (different data volumes)

**Estimated Task Breakdown**:
- **Setup**: 5 tasks (project structure, dependencies, configuration)
- **Models & Database**: 13 tasks (10 models + db_manager + db_init + Alembic)
- **Service Contracts**: 10 tasks (4 contract tests + 6 integration tests)
- **Service Implementation**: 6 tasks (discovery, analyzer, builder, engine, validator, reporter)
- **Utilities**: 3 tasks (Excel parser, type converter, config)
- **CLI Interface**: 4 tasks (main, commands, display, error handling)
- **Integration & Polish**: 13 tasks (logging, exceptions, performance, unit tests, quickstart)

**Total Estimated Output**: 54 numbered, dependency-ordered tasks in tasks.md

**Key Dependencies**:
- Database models must complete before migration engine
- File discovery must complete before schema analysis
- Schema analysis must complete before schema building
- Schema building must complete before migration engine
- Migration engine must complete before validation service
- All services must complete before CLI integration
- Basic functionality must complete before performance testing

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [x] Phase 3: Tasks generated (/tasks command)
- [x] Phase 4: Implementation complete (with architectural deviations)
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none required)

**Implementation Deviations** (Added 2025-10-11):
- [ ] ⚠ Constitutional Violation: Unit test coverage 0% (required >90%)
- [ ] ⚠ Constitutional Violation: Performance tests not implemented
- [ ] ⚠ Architectural Deviation: Production uses root scripts instead of service architecture
- [ ] ⚠ Spec Mismatch: Excel → CSV → SQL pipeline (spec describes Excel → SQL)
- [ ] ⚠ Folder Structure: Extra directories (config/, notebook/, src/database/)
- [ ] ⚠ Missing Feature: Column standardization not in original spec (44 mappings required)

---
*Based on Constitution v1.0.0 - See `.specify/memory/constitution.md`*
