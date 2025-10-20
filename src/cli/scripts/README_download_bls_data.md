# BLS OES Data Downloader

Downloads Occupational Employment and Wage Statistics (OES) data from the Bureau of Labor Statistics.

## Usage

### Download all available years (2011-2025)
```bash
python src/cli/scripts/download_bls_data.py
```

### Download specific year range
```bash
python src/cli/scripts/download_bls_data.py --start-year 2015 --end-year 2020
```

### Force re-download existing files
```bash
python src/cli/scripts/download_bls_data.py --force
```

### Custom data directory
```bash
python src/cli/scripts/download_bls_data.py --data-dir /path/to/data
```

## Features

- **Smart skip detection**: Automatically detects already downloaded files and skips them
- **Progress bars**: Visual progress for both download and extraction
- **Automatic extraction**: Unzips files and extracts Excel data files
- **Cleanup**: Automatically deletes ZIP files after extraction
- **Error handling**: Gracefully handles failed downloads (some years may not be available)
- **Detailed summary**: Shows success/skip/failure counts at the end

## File Output

Downloaded files are saved as:
- Location: `data/raw/` (by default)
- Format: `all_data_M_YYYY.xlsx` (e.g., `all_data_M_2024.xlsx`)

## Data Source

- Website: https://www.bls.gov/oes/tables.htm
- URL Pattern: `https://www.bls.gov/oes/special-requests/oesmXXall.zip`
  - Where XX = last 2 digits of the year (e.g., 24 for 2024)
- Available years: 2011-2025

## Examples

```bash
# Download just 2024 data
python src/cli/scripts/download_bls_data.py --start-year 2024 --end-year 2024

# Download last 5 years
python src/cli/scripts/download_bls_data.py --start-year 2020 --end-year 2024

# Re-download all data
python src/cli/scripts/download_bls_data.py --force
```
