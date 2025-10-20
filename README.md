# OEWS Data Pipeline

A data pipeline for processing and migrating BLS Occupational Employment and Wage Statistics (OEWS) data from Excel sources to SQL databases (SQLite/PostgreSQL), with planned support for Azure SQL Serverless deployment.

## Overview

This project provides a multi-stage pipeline for processing BLS OEWS data:
1. **Excel to CSV conversion** - Extract data from Excel workbooks
2. **Column analysis** - Inspect and document schema across files
3. **Schema standardization** - Normalize column names and types across the dataset
4. **Database migration** - Load standardized data into SQLite or PostgreSQL databases
5. **Cloud deployment** - (Planned) Deploy local SQLite databases to Azure SQL Serverless

## Features

✅ **Implemented:**
- **Batch CSV Processing**: Efficiently convert Excel files to CSV format
- **Schema Analysis**: Scan raw CSV headers and generate diagnostic reports
- **Column Standardization**: Normalize column names and data types across heterogeneous sources
- **High-Performance Migration**: Multi-threaded SQLite/PostgreSQL data loading with configurable batch sizes
- **BLS Data Download**: Utility to download data directly from BLS API
- **Command-Line Interface**: Comprehensive CLI for pipeline orchestration
- **Progress Tracking**: Real-time progress bars for long-running operations

🚧 **Planned:**
- **Azure SQL Integration**: Deploy SQLite databases to Azure SQL Serverless
- **Data Validation**: Consistency checks between source and target databases
- **Interactive UI**: Streamlit-based interface for data exploration

## Project Structure

```
src/
├── cli/
│   └── scripts/                    # Core pipeline scripts
│       ├── oews_pipeline.py        # Main pipeline orchestrator (analyze → standardize → migrate)
│       ├── analyze_columns.py      # CSV header analysis and diagnostics
│       ├── standardize_csv_columns.py  # Column name/type normalization
│       ├── migrate_csv_to_db.py    # Database loading (SQLite/PostgreSQL)
│       ├── excel_to_csv.py         # Excel to CSV batch conversion
│       ├── download_bls_data.py    # BLS API data download utility
│       └── _common.py              # Shared utilities
tests/                             # Test suite
data/                              # Data directories
├── csv/                           # Raw CSV files
├── standardized/                  # Normalized parquet files
└── oews.db                        # SQLite database (generated)
alembic/                           # Database migration scripts (for PostgreSQL)
specs/                             # Feature specifications
├── 001-interactive-data-filtering/
├── 002-i-want-to/
└── 003-hosted-sql-db/             # Azure SQL deployment spec (in progress)
requirements.txt                   # Python dependencies
pyproject.toml                     # Project metadata and build config
.env.template                      # Environment configuration template
```

## Requirements

- Python 3.10+
- SQLite (for local database) or PostgreSQL (optional, for production databases)
- For BLS data download: Internet connection
- For Azure deployment (future): Azure CLI and active Azure subscription

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/oews.git
cd oews
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. (Optional) Set up environment variables:
```bash
cp .env.template .env
# Edit .env to customize batch sizes, logging, Azure region, etc.
```

## Usage

### Running the Full Pipeline

The complete data processing pipeline in one command:

```bash
python -m src.cli.scripts.oews_pipeline all
```

This orchestrates three stages:
1. **Analyze**: Inspects raw CSV headers under `data/csv/`
2. **Standardize**: Normalizes columns and writes parquet files to `data/standardized/`
3. **Migrate**: Loads standardized data into `data/oews.db` (SQLite)

### Running Individual Stages

```bash
# Stage 1: Analyze CSV headers and document schema
python -m src.cli.scripts.oews_pipeline analyze --sample-rows 50

# Stage 2: Standardize columns to parquet (multi-threaded)
python -m src.cli.scripts.oews_pipeline standardize --workers 4

# Stage 3: Migrate parquet data into SQLite with batched inserts
python -m src.cli.scripts.oews_pipeline migrate --workers 4 --batch-size 50000
```

### Converting Excel Files to CSV

```bash
python -m src.cli.scripts.excel_to_csv [excel_directory] [output_directory]
```

### Downloading Data from BLS

```bash
python -m src.cli.scripts.download_bls_data [output_directory]
```

### Database Setup for PostgreSQL (Optional)

For production deployments using PostgreSQL with Alembic migrations:

```bash
# Initialize schema
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

## Data Source

This project uses data from the Bureau of Labor Statistics (BLS) Occupational Employment and Wage Statistics (OEWS) program. The OEWS program produces employment and wage estimates annually for over 800 occupations.

Learn more: [BLS OEWS](https://www.bls.gov/oes/)

## Development

### Running Tests

```bash
cd src && pytest
```

This runs the test suite with coverage reporting (requires 90%+ coverage to pass).

### Code Quality

```bash
# Linting with Ruff
ruff check .

# Code formatting with Black
black .

# Type checking with mypy
mypy src --strict
```

## Architecture

The pipeline follows a staged data transformation approach:

1. **Input Stage**: Excel files or CSV data in `data/csv/`
2. **Analysis Stage**: `analyze_columns.py` - Scans CSV headers, documents schema inconsistencies
3. **Standardization Stage**: `standardize_csv_columns.py` - Normalizes column names/types, outputs parquet
4. **Migration Stage**: `migrate_csv_to_db.py` - Loads standardized data into SQLite/PostgreSQL
5. **Output**: Queryable SQL database ready for analytics

Key performance optimizations:
- Multi-threaded processing (configurable worker count)
- Polars for fast CSV processing (10-100x faster than pandas)
- Batched database inserts (configurable batch size)
- Progress tracking with TQDM

## Roadmap

**Implemented (002-i-want-to):**
- [x] Excel to CSV conversion
- [x] CSV column analysis and schema documentation
- [x] Column standardization and parquet output
- [x] SQLite/PostgreSQL database migration
- [x] Multi-threaded batch processing
- [x] BLS data download utility

**In Progress (003-hosted-sql-db):**
- [ ] Azure SQL Serverless deployment
- [ ] Data validation between source and target
- [ ] Deployment automation and rollback

**Planned (001-interactive-data-filtering):**
- [ ] Interactive web UI for data exploration
- [ ] Natural language query interface
- [ ] Advanced analytics and visualizations
- [ ] Data validation reporting dashboard

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Bureau of Labor Statistics for providing the OEWS data
- Built with Python 3.10+, Polars, SQLAlchemy, Click, and Alembic
- High-performance Excel processing via fastexcel and openpyxl
- Progress tracking with TQDM

## Contact

For questions or feedback, please open an issue on GitHub.
