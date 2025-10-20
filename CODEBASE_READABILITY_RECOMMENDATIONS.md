# OEWS Codebase Readability Recommendations

## High Criticality
- `pyproject.toml:34`, `src/cli/scripts/analyze_columns.py:37`, `src/cli/scripts/standardize_csv_columns.py:27`, `src/cli/scripts/migrate_csv_to_db.py:33`: Exposed console entry point targets a non-existent module and forces every script to mutate `sys.path`; the CLI breaks once installed and must be reorganized into a proper package with clean imports.
- `alembic/env.py:1`, `alembic/versions/339b7f1f5ff3_initial_oews_migration_schema.py:32`: Alembic expects `src.models` and `Text` imports that do not exist, so migrations cannot run; without repairing these modules the database schema cannot be applied or evolved.
- `pyproject.toml:11`, `requirements.txt:10`, `src/cli/scripts/standardize_csv_columns.py:24`, `src/cli/scripts/download_bls_data.py:99`: Runtime dependencies such as `polars` and `requests` are missing from the authoritative dependency list, producing import errors when running installed commands; align dependencies to keep the pipeline usable.
- `src/cli/scripts/excel_to_csv.py:65`: When Polars import fails the pandas fallback references `safe_name` defined in the failed branch, triggering `UnboundLocalError`; restructure the function so the fallback path executes correctly on environments without Polars.

## Medium Criticality
- `src/cli/scripts/standardize_csv_columns.py:51`, `src/cli/scripts/migrate_csv_to_db.py:41`: Canonical OEWS column names, defaults, and metadata are duplicated; centralize them in a shared module to prevent schema drift.
- `src/cli/scripts/oews_pipeline.py:14`, `src/cli/scripts/excel_to_csv.py:123`, `src/cli/scripts/download_bls_data.py:189`: Commands mix Click, argparse, and ad-hoc printing with emoji; standardize on Click plus the `logging` module for consistent command-line UX.
- `src/cli/scripts/excel_to_csv.py:109`: Nested `ProcessPoolExecutor` usage and loosely typed worker parameters obscure concurrency behavior; simplify or document the strategy and type optional arguments (`Optional[int]`) for clarity.

## Low Criticality
- `src/cli/scripts/migrate_csv_to_db.py:287`: The producer/consumer queue and message kinds rely on sentinel strings; type the queue (e.g., `Queue[BatchMessage]`) or promote kinds to an `Enum` to improve readability.
- `tests/conftest.py:10`: The test suite only defines fixtures; add focused tests for each CLI stage to protect the refactors above and uphold the stated coverage goal.

---

# Action Plan to Fix Identified Issues

## Phase 1: Critical Fixes (Must Fix - Breaking Issues)

### 1.1 Fix Broken CLI Entry Point
**Issue**: `pyproject.toml:34` references non-existent `src.cli.main:main`, causing CLI to break on install.

**Root Cause**: Entry point targets a module that was never created; scripts currently run via `python -m` which bypasses the entry point.

**Action Steps**:
1. Create `src/cli/main.py` as the CLI entry point
2. Move CLI command group from `src/cli/scripts/oews_pipeline.py` to `main.py`
3. Import all commands (analyze, standardize, migrate, excel-to-csv, download-bls-data) into main CLI group
4. Update imports to be package-relative instead of using `sys.path` manipulation
5. Test installation: `pip install -e .` and verify `oews-migrate --help` works

**Files to Create/Modify**:
- Create: `src/cli/main.py` (new CLI entry point with Click command group)
- Modify: `src/cli/scripts/oews_pipeline.py` (keep subcommands, remove if-main)
- Modify: `src/cli/scripts/analyze_columns.py` (remove sys.path manipulation at line 37)
- Modify: `src/cli/scripts/standardize_csv_columns.py` (remove sys.path manipulation at line 27)
- Modify: `src/cli/scripts/migrate_csv_to_db.py` (remove sys.path manipulation at line 33)

**Expected Outcome**: Users can `pip install oews-migration` and run `oews-migrate` from anywhere without path hacks.

**Estimated Effort**: 2-3 hours

---

### 1.2 Fix Alembic Broken Imports
**Issue**: `alembic/env.py:14` imports non-existent `src.models` module, breaking database migrations.

**Root Cause**: Alembic scaffold was generated with assumption of `src.models` but actual code doesn't use ORM models (uses direct SQL instead).

**Action Steps**:
1. Create minimal `src/models/__init__.py` with SQLAlchemy Base and metadata
2. Define core table schemas using SQLAlchemy declarative models (oews_data table)
3. Update `alembic/env.py` imports to succeed
4. Review `alembic/versions/339b7f1f5ff3_*.py` and fix `Text` import (should be `from sqlalchemy import Text`)
5. Test migrations: `alembic upgrade head` should complete without errors
6. Alternative: If ORM isn't needed, remove Alembic entirely and document manual schema creation via `database_schema.sql`

**Files to Create/Modify**:
- Create: `src/models/__init__.py` (Base, metadata, imports)
- Create: `src/models/oews_data.py` (Table definition matching current schema)
- Modify: `alembic/versions/339b7f1f5ff3_initial_oews_migration_schema.py` (fix Text import)
- Update: `database_schema.sql` to match model definitions

**Expected Outcome**: `alembic upgrade head` runs successfully; PostgreSQL deployments can use migrations.

**Estimated Effort**: 3-4 hours

---

### 1.3 Align Dependencies Between pyproject.toml and requirements.txt
**Issue**: `pyproject.toml:11` missing `polars` and `requests` dependencies that are in `requirements.txt`.

**Root Cause**: Dual dependency tracking (pyproject.toml vs requirements.txt) causes drift.

**Action Steps**:
1. Add missing dependencies to `pyproject.toml` under `[project.dependencies]`:
   - `polars>=0.20.0`
   - `fastexcel>=0.10.0`
   - `requests>=2.31.0`
   - `tqdm>=4.65.0`
2. Consider deprecating `requirements.txt` in favor of single source in `pyproject.toml`
3. Add note in requirements.txt: "See pyproject.toml for canonical dependencies"
4. Test: `pip install -e .` should install all runtime deps without errors

**Files to Modify**:
- Modify: `pyproject.toml` (add polars, fastexcel, requests, tqdm to dependencies list)
- Update: `requirements.txt` (add comment pointing to pyproject.toml as canonical source)

**Expected Outcome**: Single source of truth for dependencies; `pip install -e .` installs all required packages.

**Estimated Effort**: 30 minutes

---

### 1.4 Fix UnboundLocalError in excel_to_csv.py Fallback
**Issue**: `src/cli/scripts/excel_to_csv.py:102` references `safe_name` which may not be defined if Polars import fails.

**Root Cause**: Variable `safe_name` is defined inside Polars try-block (line 69), but pandas fallback assumes it exists.

**Action Steps**:
1. Move `safe_name` definition BEFORE the Polars try-except block
2. Extract filename sanitization into a helper function: `_sanitize_sheet_name(sheet_name: str) -> str`
3. Call helper at start of function: `safe_name = _sanitize_sheet_name(sheet_name)`
4. Add test case that simulates Polars failure to verify pandas fallback works

**Files to Modify**:
- Modify: `src/cli/scripts/excel_to_csv.py:65-103` (restructure process_sheet function)

**Expected Outcome**: Pandas fallback works correctly when Polars unavailable; no UnboundLocalError.

**Estimated Effort**: 30 minutes

---

## Phase 2: Maintainability Improvements (Should Fix)

### 2.1 Centralize OEWS Schema Definitions
**Issue**: Column names, types, and defaults duplicated across `standardize_csv_columns.py:51` and `migrate_csv_to_db.py:41`.

**Root Cause**: No shared schema module; each script independently defines canonical columns.

**Action Steps**:
1. Create `src/schema/__init__.py` with:
   - `CANONICAL_COLUMNS: List[str]` - normalized column name list
   - `COLUMN_TYPES: Dict[str, str]` - SQLite type mappings
   - `COLUMN_DEFAULTS: Dict[str, Any]` - default values for missing columns
   - `POLARS_SCHEMA: Dict[str, pl.DataType]` - Polars schema for parquet
2. Import schema constants in both scripts
3. Replace hardcoded column lists with imports
4. Add schema version constant for future migrations

**Files to Create/Modify**:
- Create: `src/schema/__init__.py` (centralized schema definitions)
- Modify: `src/cli/scripts/standardize_csv_columns.py` (import CANONICAL_COLUMNS, POLARS_SCHEMA)
- Modify: `src/cli/scripts/migrate_csv_to_db.py` (import CANONICAL_COLUMNS, COLUMN_TYPES)

**Expected Outcome**: Single source of truth for OEWS schema; changes propagate automatically.

**Estimated Effort**: 2 hours

---

### 2.2 Standardize CLI Framework (Click + Logging)
**Issue**: Scripts mix Click, argparse, print statements, and emoji for user feedback.

**Root Cause**: Scripts evolved independently with different CLI patterns.

**Action Steps**:
1. Standardize all commands on Click (remove any argparse usage)
2. Create `src/cli/logging_config.py` with shared logging setup:
   - Configure formatters for console vs file
   - Set levels via environment variable
   - Add progress bar integration with logging
3. Replace print/emoji statements with proper logging:
   - `logger.info()` for progress updates
   - `logger.warning()` for non-fatal issues
   - `logger.error()` for failures
4. Use Click's `echo()` only for final user-facing output
5. Add `--verbose` / `--quiet` flags to main CLI group

**Files to Create/Modify**:
- Create: `src/cli/logging_config.py` (shared logging configuration)
- Modify: `src/cli/scripts/oews_pipeline.py:14` (use logging instead of print)
- Modify: `src/cli/scripts/excel_to_csv.py:123` (use logging, remove emoji)
- Modify: `src/cli/scripts/download_bls_data.py:189` (use logging instead of print)
- Modify: All scripts to accept `--verbose` flag

**Expected Outcome**: Consistent CLI UX; proper log levels; parseable output for automation.

**Estimated Effort**: 4 hours

---

### 2.3 Document and Type Concurrency Strategy
**Issue**: `excel_to_csv.py:109` uses nested ProcessPoolExecutor with unclear worker parameters.

**Root Cause**: Multiprocessing code lacks documentation and type hints for optional parameters.

**Action Steps**:
1. Add comprehensive docstring to `convert_excel_to_csv()` explaining:
   - Why ProcessPoolExecutor is used (CPU-bound Excel parsing)
   - Worker count calculation logic (defaults to CPU count)
   - Memory considerations for concurrent processing
2. Type all optional parameters: `max_workers: Optional[int] = None`
3. Extract worker count calculation to named function: `_calculate_workers(max_workers: Optional[int]) -> int`
4. Add inline comments explaining multiprocessing strategy
5. Consider adding `--max-workers` CLI flag for user control

**Files to Modify**:
- Modify: `src/cli/scripts/excel_to_csv.py:109` (add types, docs, extract logic)

**Expected Outcome**: Clear concurrency strategy; type-safe parameters; user can control parallelism.

**Estimated Effort**: 1.5 hours

---

## Phase 3: Code Quality Polish (Nice to Have)

### 3.1 Type Queue Messages with Enum
**Issue**: `migrate_csv_to_db.py:287` uses string sentinels for queue messages ("DONE", "ERROR").

**Root Cause**: No structured message types; relies on magic strings.

**Action Steps**:
1. Create `src/cli/scripts/_types.py` with:
   - `class MessageKind(Enum)`: BATCH, DONE, ERROR
   - `@dataclass BatchMessage`: kind, table_name, batch_data, row_count
2. Type the queue: `queue: Queue[BatchMessage] = Queue()`
3. Replace string sentinels with typed messages
4. Update producer/consumer to handle typed messages

**Files to Create/Modify**:
- Create: `src/cli/scripts/_types.py` (message types and enums)
- Modify: `src/cli/scripts/migrate_csv_to_db.py:287` (use typed queue)

**Expected Outcome**: Type-safe message passing; no magic strings; IDE autocomplete for message fields.

**Estimated Effort**: 2 hours

---

### 3.2 Add Integration Tests for CLI Stages
**Issue**: `tests/conftest.py:10` only has fixtures; no actual tests for CLI commands.

**Root Cause**: Test suite not expanded beyond initial setup.

**Action Steps**:
1. Create `tests/test_analyze_columns.py`:
   - Test analyze command with sample CSV files
   - Verify output diagnostic files created
   - Check column inventory accuracy
2. Create `tests/test_standardize_columns.py`:
   - Test standardization with known CSV inputs
   - Verify parquet output schema matches canonical
   - Test multi-threading with workers=2
3. Create `tests/test_migrate_to_db.py`:
   - Test SQLite migration with sample parquet files
   - Verify row counts match input
   - Test batch processing logic
4. Create `tests/test_pipeline_integration.py`:
   - Test full pipeline end-to-end
   - Verify data integrity from CSV → DB
5. Target 90%+ coverage per pyproject.toml config

**Files to Create**:
- Create: `tests/test_analyze_columns.py`
- Create: `tests/test_standardize_columns.py`
- Create: `tests/test_migrate_to_db.py`
- Create: `tests/test_pipeline_integration.py`
- Create: `tests/fixtures/` (sample CSV/parquet data for testing)

**Expected Outcome**: Comprehensive test coverage; regression protection; CI/CD confidence.

**Estimated Effort**: 8-10 hours

---

## Execution Order

**Week 1: Critical Fixes (Must complete)**
1. Day 1-2: Fix CLI entry point (1.1) + Align dependencies (1.3)
2. Day 3: Fix excel_to_csv fallback bug (1.4)
3. Day 4-5: Fix Alembic migrations (1.2) OR remove Alembic if not needed

**Week 2: Maintainability (High value)**
1. Day 1: Centralize schema definitions (2.1)
2. Day 2-3: Standardize logging (2.2)
3. Day 4: Document concurrency (2.3)

**Week 3: Polish (As time permits)**
1. Day 1: Type queue messages (3.1)
2. Day 2-5: Write integration tests (3.2)

---

## Success Criteria

- [ ] `pip install -e .` succeeds without errors
- [ ] `oews-migrate --help` displays all commands
- [ ] `alembic upgrade head` completes successfully (or Alembic removed with docs)
- [ ] All CLI commands have consistent logging output
- [ ] Test coverage ≥ 90% (per pyproject.toml config)
- [ ] No `sys.path` manipulation in any script
- [ ] Schema changes only need updates in one location (src/schema/)
- [ ] CI/CD pipeline passes all tests

---

## Notes

- **Dependency Management**: Consider fully migrating to pyproject.toml and removing requirements.txt for single source of truth
- **Alembic Decision**: Evaluate if Alembic is needed; current code uses direct SQL which may be sufficient for SQLite-focused workflow
- **Testing Data**: Create minimal synthetic OEWS CSV samples for tests (avoid committing large real data files)
- **Documentation**: Update README.md after Phase 1 to reflect working installation instructions

---

## Evaluation of Proposed Plan

**What Works**
- `CODEBASE_READABILITY_RECOMMENDATIONS.md:80`: Updating dependency management directly addresses the missing runtime packages, though remember `pyproject.toml:19` already lists `tqdm>=4.65.0`.
- `CODEBASE_READABILITY_RECOMMENDATIONS.md:99`: The excel fallback fix (promoting `_sanitize_sheet_name`) resolves the `UnboundLocalError` and keeps both code paths readable and testable.
- `CODEBASE_READABILITY_RECOMMENDATIONS.md:121`: Creating a shared schema module prevents divergence between the standardizer and migrator, aligning with the earlier recommendation to centralize column metadata.
- `CODEBASE_READABILITY_RECOMMENDATIONS.md:265`: The execution order prioritizes the high-severity breakages first, so the pipeline becomes functional before tackling polish items.

**Risks / Gaps**
- `CODEBASE_READABILITY_RECOMMENDATIONS.md:147`: Migrating every script to Click will break direct `argparse` entrypoints (`python -m …`) unless you provide compatibility shims or a clear migration path for existing automation.
- `CODEBASE_READABILITY_RECOMMENDATIONS.md:178`: Documenting/typing concurrency is good, but without tests covering both default and custom worker counts, regressions could slip through; add smoke tests to exercise those variations.
- `CODEBASE_READABILITY_RECOMMENDATIONS.md:204`: Introducing `src/cli/scripts/_types.py` solely for the queue enum may be heavier than needed; consider colocating the enum with `BatchMessage` unless more shared types emerge.
- `CODEBASE_READABILITY_RECOMMENDATIONS.md:227`: The 8–10 hour estimate for full integration tests may be optimistic once fixture creation is included; plan for extra time or bootstrap with focused unit tests before full end-to-end coverage.
