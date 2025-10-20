### **Project Refactor: OEWS Data Pipeline**

#### **Executive Summary**

The goal of this project is to refactor the existing set of OEWS data processing scripts into a robust, reliable, and maintainable Python package. The current implementation suffers from critical breakages, inconsistent patterns, and a lack of tests that make it fragile and difficult to share or deploy.

This three-phase plan addresses these issues systematically. **Phase 1** focuses on immediate stabilization by creating a proper package structure and fixing broken dependencies. **Phase 2** improves maintainability by centralizing configuration and standardizing interfaces. **Phase 3** hardens the codebase by introducing comprehensive testing.

The outcome will be a professional-grade command-line application that is easy to install, use, and extend.

---

### **Phase 1: Stabilize the Foundation (Week 1)**

This phase resolves critical breakages that prevent the application from being installed or run reliably.

1.  **Establish a Proper Package Structure & Fix Dependencies:**
    *   **Action:** Create a unified CLI entry point at `src/cli/main.py`. Move the core command logic from the individual scripts into this main file to create a single, coherent command-line interface (e.g., `oews-migrate standardize`, `oews-migrate download`).
    *   **Justification:** This eliminates all `sys.path` manipulation, making the package import system reliable. It also resolves the broken `pyproject.toml` entry points.
    *   **Action:** Consolidate all runtime dependencies (`polars`, `requests`, etc.) into the `pyproject.toml` file, making it the single source of truth. Deprecate `requirements.txt`.
    *   **Justification:** This fixes installation errors and aligns with modern Python packaging standards.

2.  **Simplify Database Schema Management:**
    *   **Action:** Remove the Alembic integration. The current migration files are broken and reference deleted models. Given the project's scope, the complexity of maintaining ORM-based migrations is unnecessary.
    *   **Justification:** This significantly reduces maintenance overhead. The existing `database_schema.sql` file is sufficient for documenting and creating the schema manually, which is a simpler and more direct approach for this project.

3.  **Fix `UnboundLocalError` in CSV Conversion:**
    *   **Action:** Refactor the `excel_to_csv.py` script to define the `safe_name` variable *before* the `try/except` block for the Polars import.
    *   **Justification:** This corrects a critical bug that causes the script to crash if the Polars library is not installed.

---

### **Phase 2: Improve Maintainability & Consistency (Week 2)**

This phase focuses on refactoring to eliminate duplicated code and inconsistent user experiences.

1.  **Centralize Schema Definitions:**
    *   **Action:** Create a new module (e.g., `src/oews_schema.py`) to act as the single source of truth for all database column names, data types, and default values.
    *   **Justification:** This eliminates schema duplication between the `standardize` and `migrate` scripts, preventing future inconsistencies and making schema changes trivial.

2.  **Standardize the Command-Line Interface:**
    *   **Action:** Refactor all scripts to use the `logging` module for all informational output, warnings, and errors. Remove all ad-hoc `print()` statements and emojis. Standardize on Click for all command-line interaction.
    *   **Justification:** This provides a consistent, professional CLI experience and allows for structured, machine-readable output, which is critical for automation and debugging. We will deprecate direct script execution via `python -m` in favor of the new, unified entry point.

3.  **Clarify Concurrency Logic:**
    *   **Action:** Add a detailed docstring and inline comments to the `excel_to_csv.py` script to explain the `ProcessPoolExecutor` strategy. Add type hints for all function parameters (`max_workers: Optional[int]`).
    *   **Justification:** This makes the complex concurrency logic understandable and safer to modify in the future.

---

### **Phase 3: Harden & Automate (Week 3 & Beyond)**

This phase introduces a testing framework to ensure long-term quality and prevent regressions.

1.  **Introduce Foundational Testing:**
    *   **Action:** Create a `tests/` directory with an initial set of focused unit tests for the most critical and complex logic, such as the Polars/pandas fallback in `excel_to_csv.py` and the schema standardization logic.
    *   **Justification:** This provides an immediate safety net for the most important parts of the codebase. While the original estimate of 8-10 hours for full integration tests is optimistic, establishing a foundation of unit tests is a pragmatic first step.

2.  **Improve Internal Data Structures:**
    *   **Action:** In `migrate_csv_to_db.py`, convert the string-based queue messages ("DONE") to a more robust `Enum`. This `Enum` can be defined directly within the script to avoid creating a new file for a single type.
    *   **Justification:** This improves type safety and readability by eliminating "magic strings."

3.  **Expand Test Coverage (Stretch Goal):**
    *   **Action:** After foundational tests are in place, incrementally add integration tests for each CLI command, using small, synthetic data files as fixtures.
    *   **Justification:** This will build confidence for future refactoring and ensure the entire data pipeline works as expected from end to end.

---

### **Success Metrics**

The project will be considered a success when:
- The package can be installed without errors using `pip install -e .`.
- The main CLI entry point (`oews-migrate --help`) is functional and displays all commands.
- All `sys.path` manipulation is removed.
- The database schema is managed by a single, documented SQL file.
- All commands produce consistent, logged output.
- A foundational test suite is in place and passes, providing a basis for achieving >90% coverage.
