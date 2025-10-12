# Research Findings: OEWS Excel to SQL Database Migration

**Date**: 2025-10-02
**Feature**: OEWS Excel to SQL Database Migration Application

## Technology Stack Research

### Excel Processing Library
**Decision**: pandas + openpyxl
**Rationale**: pandas provides robust data analysis and manipulation capabilities with excellent Excel support via openpyxl. Handles both .xls and .xlsx formats with schema inference and data type detection.
**Alternatives considered**: xlrd/xlwt (deprecated for .xlsx), python-excel (limited functionality), xlsxwriter (write-only)

### Database ORM and Connectivity
**Decision**: SQLAlchemy Core + Engine
**Rationale**: Aligns with constitutional requirements for SQLAlchemy ORM. Provides database abstraction, connection pooling, and transaction management. Core API gives precise control for schema creation and bulk operations.
**Alternatives considered**: Raw database drivers (no abstraction), Django ORM (too heavy for CLI), Peewee (smaller ecosystem)

### Database Backend
**Decision**: SQLite for development, PostgreSQL for production
**Rationale**: SQLite provides zero-configuration setup for development and testing. PostgreSQL offers production-grade performance, ACID compliance, and better concurrent access for large datasets.
**Alternatives considered**: MySQL (licensing concerns), SQL Server (platform limitations)

### CLI Framework
**Decision**: argparse + click
**Rationale**: argparse is built-in for basic argument parsing. click provides enhanced CLI features like progress bars, colored output, and command grouping without external dependencies.
**Alternatives considered**: typer (newer but less mature), fire (too magic), pure argparse (limited features)

### Schema Analysis Strategy
**Decision**: Statistical sampling + heuristic type inference
**Rationale**: Analyze representative samples from each Excel file to infer column types and relationships. Use pandas data type inference combined with domain-specific heuristics for OEWS data patterns.
**Alternatives considered**: Full file scan (performance impact), manual schema definition (maintenance burden), ML-based inference (complexity overhead)

## Data Processing Patterns

### Memory Management
**Decision**: Chunked processing with configurable batch sizes
**Rationale**: Process large Excel files in chunks to stay within 1.75GB memory limit. Default 10,000 record batches with adaptive sizing based on available memory.
**Alternatives considered**: Full file loading (memory issues), streaming (complexity), external sorting (disk I/O overhead)

### Error Handling Strategy
**Decision**: Exception hierarchy with continuation policies
**Rationale**: Define specific exception types for different error scenarios (file access, data validation, database constraints). Implement configurable policies for handling each error type.
**Alternatives considered**: Generic exception handling (poor diagnostics), fail-fast (user hostile), silent errors (data integrity risk)

### Transaction Management
**Decision**: Per-file transactions with savepoints
**Rationale**: Each Excel file migration runs in its own transaction with savepoints for rollback capability. Enables per-file rollback while maintaining overall consistency.
**Alternatives considered**: Single transaction (all-or-nothing), per-record transactions (performance impact), no transactions (consistency risk)

## Performance Optimization

### Bulk Operations
**Decision**: SQLAlchemy bulk insert with executemany()
**Rationale**: Use bulk insert operations for maximum database performance. Batch sizes tuned for optimal throughput while respecting memory constraints.
**Alternatives considered**: Individual inserts (slow), pandas to_sql (less control), copy operations (database-specific)

### Indexing Strategy
**Decision**: Delayed index creation after bulk load
**Rationale**: Create indexes after data loading for better performance. Identify key columns for indexing based on duplicate detection and validation query patterns.
**Alternatives considered**: Pre-created indexes (slower inserts), no indexes (slow queries), partial indexes (complexity)

### Caching
**Decision**: LRU cache for schema analysis results
**Rationale**: Cache expensive schema analysis operations using functools.lru_cache. Cache Excel file metadata to avoid repeated analysis.
**Alternatives considered**: No caching (repeated work), external cache (complexity), unlimited cache (memory growth)

## Architecture Patterns

### Service Layer Design
**Decision**: Service-oriented architecture with dependency injection
**Rationale**: Separate services for file discovery, schema analysis, migration, and validation. Use dependency injection for testability and modularity.
**Alternatives considered**: Monolithic design (tight coupling), microservices (overkill), functional approach (state management complexity)

### Configuration Management
**Decision**: Environment variables + YAML config files
**Rationale**: Environment variables for secrets and deployment settings. YAML files for application configuration with reasonable defaults.
**Alternatives considered**: JSON config (no comments), INI files (limited structure), command-line only (complexity)

### Logging Strategy
**Decision**: Structured logging with JSON format
**Rationale**: Use Python logging with structured JSON output for better parsing and analysis. Include correlation IDs for tracking migrations.
**Alternatives considered**: Plain text logs (harder to parse), external logging service (complexity), no logging (debugging difficulty)

## Testing Strategy

### Test Data Generation
**Decision**: Actual OEWS public data for testing
**Rationale**: Use real OEWS Excel files from data/ directory (2011-2024) since all data is public and contains authentic structure patterns. Files are 70-80MB each with 400K+ records, perfect for testing performance requirements.
**Alternatives considered**: Synthetic data (missing real-world edge cases), minimal test data (insufficient coverage), manual test data (maintenance burden)

### Real OEWS Data Structure Analysis
**Findings from data/all_data_M_2024.xlsx**:
- **File Structure**: 4 sheets: "All May 2024 data", "Field Descriptions", "UpdateTime", "Filler"
- **Data Volume**: 414,437 records, ~518MB in memory, 75MB Excel file
- **Column Structure**: 32 standardized columns across all years (2011-2024)
- **Key Columns**: AREA, AREA_TITLE, OCC_CODE, OCC_TITLE, TOT_EMP, A_MEAN, H_MEAN, NAICS, etc.
- **Data Types**: Mixed (text, integers, decimals, special values like '#' for suppressed data)
- **Occupation Codes**: SOC-based (e.g., "11-1011" for Chief Executives)
- **Geographic Coverage**: US national, state, and metropolitan areas
- **Industry Coverage**: Cross-industry and NAICS-specific data
- **Consistency**: Column structure stable across 2011-2024 files

**Test Data Strategy**:
1. **Unit Tests**: Use subsets of real data (100-500 records) for specific scenarios
2. **Integration Tests**: Use full files (70MB) to test performance and memory constraints
3. **Performance Tests**: Multi-file scenarios using 2-3 actual OEWS files
4. **Edge Case Tests**: Focus on special values ('#', NaN, empty strings) found in real data
5. **Schema Evolution Tests**: Compare structure changes between different years (2011 vs 2024)

### Database Testing
**Decision**: In-memory SQLite for unit tests, Docker PostgreSQL for integration
**Rationale**: Fast in-memory databases for unit tests. Dockerized PostgreSQL for integration tests that need production database features.
**Alternatives considered**: Test databases (cleanup complexity), mocking (insufficient coverage), production database (safety risk)

### Performance Testing
**Decision**: pytest-benchmark with realistic data volumes
**Rationale**: Automated performance testing with benchmark comparisons. Test with data volumes matching production requirements (70MB files).
**Alternatives considered**: Manual timing (inconsistent), production monitoring only (late feedback), load testing tools (overkill)

## Implementation Sequence

1. **Core Models**: Define SQLAlchemy models for tracking and schema
2. **File Discovery**: Implement Excel file enumeration with filtering
3. **Schema Analysis**: Build type inference and relationship detection
4. **Database Schema**: Create unified schema generation logic
5. **Migration Engine**: Implement core data transfer with error handling
6. **Validation**: Build consistency checking and reporting
7. **CLI Interface**: Create user-friendly command-line interface
8. **Rollback System**: Implement per-file transaction rollback
9. **Performance Optimization**: Add chunking and bulk operations
10. **Comprehensive Testing**: Unit, integration, and performance tests

This research provides the foundation for detailed design and implementation planning in Phase 1.