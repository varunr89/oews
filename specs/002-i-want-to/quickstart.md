# Quickstart Guide: OEWS Excel to SQL Database Migration

**Date**: 2025-10-02
**Feature**: OEWS Excel to SQL Database Migration Application

## Prerequisites

### System Requirements
- Python 3.10 or higher
- 4GB available RAM minimum
- 10GB free disk space for temporary processing
- Read access to OEWS Excel files directory
- Database server (SQLite for development, PostgreSQL for production)

### Dependencies Installation
```bash
pip install -r requirements.txt
```

Required packages:
- pandas>=1.5.0
- openpyxl>=3.0.0
- sqlalchemy>=2.0.0
- click>=8.0.0
- python-dotenv>=0.19.0

## Quick Start (5 minutes)

### 1. Basic Setup
```bash
# Clone and setup
git clone <repository>
cd oews-migration
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration
Create `.env` file in project root:
```
DATABASE_URL=sqlite:///oews_migration.db
LOG_LEVEL=INFO
MAX_MEMORY_USAGE=1073741824
BATCH_SIZE=10000
```

### 3. Run Your First Migration
```bash
# Discover Excel files
python -m src.cli.main discover --directory /path/to/excel/files

# Analyze schemas
python -m src.cli.main analyze --directory /path/to/excel/files

# Create unified schema
python -m src.cli.main create-schema --name oews_unified

# Migrate data
python -m src.cli.main migrate --directory /path/to/excel/files --schema oews_unified

# Validate results
python -m src.cli.main validate --batch-id <batch-uuid>
```

## Detailed Walkthrough (30 minutes)

### Step 1: File Discovery and Analysis

**Objective**: Discover all OEWS Excel files and analyze their structure

```bash
# Discover files with options
python -m src.cli.main discover \
    --directory /data/oews \
    --recursive \
    --max-size 100MB \
    --exclude-pattern "temp_*" \
    --output discovery_report.json

# Expected output: 50-100 Excel files discovered
# Example: Found 73 Excel files totaling 486MB
```

**Validation Checkpoint**:
- [ ] All expected Excel files are discovered
- [ ] No permission errors encountered
- [ ] Total file size matches expectations (~700MB for 10 years)
- [ ] Discovery report contains file metadata

### Step 2: Schema Analysis

**Objective**: Analyze Excel file structures and infer data types

```bash
# Analyze schemas with detailed options
python -m src.cli.main analyze \
    --directory /data/oews \
    --sample-size 1000 \
    --confidence-threshold 0.8 \
    --output schema_analysis.json

# Expected output: Schema analysis for all files
# Example: Analyzed 73 files, found 245 unique columns across 15 sheet types
```

**Validation Checkpoint**:
- [ ] Schema analysis completes without errors
- [ ] Column types are inferred correctly (verify sample)
- [ ] Relationships between files are identified
- [ ] Common OEWS patterns recognized (occupation codes, wage data, etc.)

### Step 3: Unified Schema Creation

**Objective**: Create a unified database schema accommodating all Excel files

```bash
# Create unified schema
python -m src.cli.main create-schema \
    --name oews_unified \
    --input schema_analysis.json \
    --normalize-names \
    --add-indexes \
    --output unified_schema.sql

# Expected output: SQL schema definition
# Example: Created unified schema with 12 tables, 89 columns, 15 indexes
```

**Validation Checkpoint**:
- [ ] Unified schema accommodates all discovered columns
- [ ] Data types are appropriate for OEWS data
- [ ] Primary keys and foreign keys are defined
- [ ] Indexes are created for performance

### Step 4: Data Migration

**Objective**: Migrate all Excel data to the unified database schema

```bash
# Start migration with comprehensive options
python -m src.cli.main migrate \
    --directory /data/oews \
    --schema oews_unified \
    --batch-size 10000 \
    --skip-duplicates \
    --enable-rollback \
    --validate-data \
    --progress \
    --output migration_log.json

# Expected output: Migration progress and completion
# Example: Migrated 1,234,567 records from 73 files in 45 minutes
```

**Validation Checkpoint**:
- [ ] Migration completes successfully
- [ ] Expected number of records migrated
- [ ] No critical errors in migration log
- [ ] Database contains expected data volume
- [ ] Rollback checkpoints created

### Step 5: Data Validation

**Objective**: Validate data integrity and migration accuracy

```bash
# Run comprehensive validation
python -m src.cli.main validate \
    --batch-id <migration-batch-id> \
    --level comprehensive \
    --sample-percentage 10 \
    --output validation_report.html

# Expected output: Validation report with data integrity score
# Example: Validation passed with 99.8% data integrity score
```

**Validation Checkpoint**:
- [ ] Data integrity score > 95%
- [ ] No referential integrity violations
- [ ] Source-target data comparison passes
- [ ] Business rule validation passes
- [ ] Validation report generated

### Step 6: Incremental Migration Test

**Objective**: Test incremental migration with new files

```bash
# Add new Excel file and run incremental migration
cp new_oews_2024.xlsx /data/oews/
python -m src.cli.main migrate \
    --directory /data/oews \
    --schema oews_unified \
    --incremental \
    --overwrite-existing

# Expected output: Only new file processed
# Example: Processed 1 new file, updated 15,432 existing records
```

**Validation Checkpoint**:
- [ ] Only new/changed files are processed
- [ ] Existing records updated correctly
- [ ] No duplicate data created
- [ ] Migration performance within limits

## Common Operations

### Check Migration Status
```bash
python -m src.cli.main status --batch-id <batch-uuid>
```

### Export Validation Report
```bash
python -m src.cli.main export-report \
    --batch-id <batch-uuid> \
    --format pdf \
    --output migration_report.pdf
```

### Rollback Migration
```bash
python -m src.cli.main rollback \
    --file-path /data/oews/file.xlsx \
    --checkpoint <checkpoint-id>
```

### Monitor Real-time Progress
```bash
python -m src.cli.main monitor --batch-id <batch-uuid>
```

## Performance Expectations

### Typical Performance Metrics
- **File Discovery**: 1-2 seconds per 100 files
- **Schema Analysis**: 5-10 seconds per file
- **Migration**: 10,000-50,000 records per minute
- **Validation**: 2-5 minutes for comprehensive validation
- **Memory Usage**: Peak 1.2GB for 70MB files

### Optimization Tips
- Use SSD storage for better I/O performance
- Increase batch size for large files (up to 50,000)
- Enable parallel validation for faster checking
- Use PostgreSQL for production (better performance than SQLite)

## Troubleshooting

### Common Issues

**"Memory usage exceeded limit"**
```bash
# Reduce batch size
python -m src.cli.main migrate --batch-size 5000
```

**"Schema incompatibility detected"**
```bash
# Check schema analysis
python -m src.cli.main analyze --verbose
# Manually review unified_schema.sql
```

**"Validation failed with errors"**
```bash
# Get detailed validation report
python -m src.cli.main validate --level exhaustive --detailed
```

### Getting Help
```bash
python -m src.cli.main --help
python -m src.cli.main migrate --help
```

## Success Criteria

At the end of this quickstart, you should have:
- [ ] Successfully discovered all OEWS Excel files
- [ ] Created a unified database schema
- [ ] Migrated all data with >95% integrity score
- [ ] Generated comprehensive validation reports
- [ ] Tested incremental migration functionality
- [ ] Demonstrated rollback capability

**Total Time**: 30-45 minutes for initial setup and first migration
**Data Volume**: Up to 700MB (10 years of OEWS data)
**Success Rate**: >99% data integrity with proper validation

This quickstart demonstrates the complete end-to-end migration workflow and validates all functional requirements are working correctly.