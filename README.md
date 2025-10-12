# OEWS Data Agent

A public data agent capable of answering questions based on Bureau of Labor Statistics (BLS) Occupational Employment and Wage Statistics (OEWS) data.

## Overview

This project provides a comprehensive solution for migrating BLS OEWS data from Excel files to a SQL database and building an intelligent data agent on top of it. The system handles data discovery, schema normalization, migration, and validation to make OEWS data accessible and queryable.

## Features

- **Automated Data Discovery**: Scan directories for OEWS Excel files
- **Schema Analysis**: Automatically analyze and normalize column schemas across multiple Excel files
- **Data Migration**: Migrate Excel data to SQL database (SQLite/PostgreSQL)
- **Data Validation**: Built-in consistency checks and validation reports
- **CLI Tools**: Command-line interface for all operations
- **Interactive UI**: Streamlit-based interface for data exploration and analysis

## Project Structure

```
.
├── src/
│   ├── cli/                # Command-line interface
│   │   ├── commands.py     # CLI commands
│   │   ├── config.py       # CLI configuration
│   │   └── scripts/        # Migration and analysis scripts
│   ├── database/           # Database management
│   │   ├── connection.py   # Database connections
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── loader.py       # Data loading utilities
│   │   └── schema.py       # Schema definitions
│   ├── models/             # Data models
│   │   ├── excel_file.py
│   │   ├── migration_record.py
│   │   ├── validation_report.py
│   │   └── unified_schema.py
│   ├── services/           # Core services
│   │   ├── file_discovery.py    # File discovery service
│   │   ├── migration_engine.py  # Data migration engine
│   │   ├── schema_analyzer.py   # Schema analysis
│   │   ├── schema_builder.py    # Schema construction
│   │   └── validator.py         # Data validation
│   └── lib/                # Shared utilities
├── tests/                  # Test suite
├── requirements.txt        # Python dependencies
└── pyproject.toml         # Project metadata

```

## Requirements

- Python 3.10+
- SQLite or PostgreSQL

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

4. Set up environment variables:
```bash
cp .env.template .env
# Edit .env with your configuration
```

## Usage

### Data Migration

1. **Convert Excel to CSV**:
```bash
python src/cli/scripts/excel_to_csv.py --input-dir /path/to/excel/files
```

2. **Analyze Column Schemas**:
```bash
python src/cli/scripts/analyze_columns.py --input-dir /path/to/csv/files
```

3. **Standardize Columns**:
```bash
python src/cli/scripts/standardize_csv_columns.py --input-dir /path/to/csv/files
```

4. **Migrate to Database**:
```bash
python src/cli/scripts/migrate_csv_to_db.py --input-dir /path/to/csv/files --db-url sqlite:///oews.db
```

### Database Management

```bash
# Initialize database
python manage_db.py init

# Run migrations
alembic upgrade head
```

### Interactive UI

```bash
streamlit run app.py
```

## Data Source

This project uses data from the Bureau of Labor Statistics (BLS) Occupational Employment and Wage Statistics (OEWS) program. The OEWS program produces employment and wage estimates annually for over 800 occupations.

Learn more: [BLS OEWS](https://www.bls.gov/oes/)

## Development

### Running Tests

```bash
cd src
pytest
```

### Code Quality

```bash
# Linting
ruff check .

# Formatting
black .
```

## Architecture

The system follows a service-oriented architecture:

1. **File Discovery Service**: Scans and catalogs Excel files
2. **Schema Analyzer**: Analyzes column structures across files
3. **Schema Builder**: Creates unified schema definitions
4. **Migration Engine**: Handles data transformation and loading
5. **Validator**: Performs data consistency checks

## Roadmap

- [x] Excel to SQL migration pipeline
- [x] Data validation and consistency checks
- [ ] Natural language query interface
- [ ] Advanced analytics and visualizations
- [ ] API endpoints for data access
- [ ] Multi-source data integration

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Bureau of Labor Statistics for providing the OEWS data
- Built with Python, pandas, SQLAlchemy, and Streamlit

## Contact

For questions or feedback, please open an issue on GitHub.