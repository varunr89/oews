"""Convert Excel files to CSV with standardized column names - MUCH FASTER"""
import pandas as pd
from pathlib import Path

# Column mapping
COLUMN_MAPPING = {
    'area': 'AREA', 'AREA': 'AREA',
    'area_title': 'AREA_TITLE', 'AREA_TITLE': 'AREA_TITLE',
    'area_type': 'AREA_TYPE', 'AREA_TYPE': 'AREA_TYPE',
    'naics': 'NAICS', 'NAICS': 'NAICS',
    'naics_title': 'NAICS_TITLE', 'NAICS_TITLE': 'NAICS_TITLE',
    'own_code': 'OWN_CODE', 'OWN_CODE': 'OWN_CODE',
    'occ code': 'OCC_CODE', 'occ_code': 'OCC_CODE', 'OCC_CODE': 'OCC_CODE',
    'occ title': 'OCC_TITLE', 'occ_title': 'OCC_TITLE', 'OCC_TITLE': 'OCC_TITLE',
    'group': 'O_GROUP', 'GROUP': 'O_GROUP',
    'o_group': 'O_GROUP', 'O_GROUP': 'O_GROUP',
    'i_group': 'I_GROUP', 'I_GROUP': 'I_GROUP',
    'tot_emp': 'TOT_EMP', 'TOT_EMP': 'TOT_EMP',
    'emp_prse': 'EMP_PRSE', 'EMP_PRSE': 'EMP_PRSE',
    'jobs_1000': 'JOBS_1000', 'JOBS_1000': 'JOBS_1000',
    'jobs_1000_orig': 'JOBS_1000',
    'LOC_Q': 'LOC_QUOTIENT', 'loc_quotient': 'LOC_QUOTIENT', 'LOC_QUOTIENT': 'LOC_QUOTIENT',
    'pct_tot': 'PCT_TOTAL', 'PCT_TOT': 'PCT_TOTAL',
    'pct_total': 'PCT_TOTAL', 'PCT_TOTAL': 'PCT_TOTAL',
    'h_mean': 'H_MEAN', 'H_MEAN': 'H_MEAN',
    'a_mean': 'A_MEAN', 'A_MEAN': 'A_MEAN',
    'mean_prse': 'MEAN_PRSE', 'MEAN_PRSE': 'MEAN_PRSE',
    'h_pct10': 'H_PCT10', 'H_PCT10': 'H_PCT10',
    'h_pct25': 'H_PCT25', 'H_PCT25': 'H_PCT25',
    'h_median': 'H_MEDIAN', 'H_MEDIAN': 'H_MEDIAN',
    'h_pct75': 'H_PCT75', 'H_PCT75': 'H_PCT75',
    'h_pct90': 'H_PCT90', 'H_PCT90': 'H_PCT90',
    'a_pct10': 'A_PCT10', 'A_PCT10': 'A_PCT10',
    'a_pct25': 'A_PCT25', 'A_PCT25': 'A_PCT25',
    'a_median': 'A_MEDIAN', 'A_MEDIAN': 'A_MEDIAN',
    'a_pct75': 'A_PCT75', 'A_PCT75': 'A_PCT75',
    'a_pct90': 'A_PCT90', 'A_PCT90': 'A_PCT90',
    'annual': 'ANNUAL', 'ANNUAL': 'ANNUAL',
    'hourly': 'HOURLY', 'HOURLY': 'HOURLY',
    'PRIM_STATE': 'PRIM_STATE',
    'PCT_RPT': 'PCT_RPT',
}

data_dir = Path('data')
csv_dir = Path('data_csv')
csv_dir.mkdir(exist_ok=True)

excel_files = sorted([f for f in data_dir.glob('*.xlsx') if not f.name.endswith('.backup')])

print(f"Converting {len(excel_files)} Excel files to CSV with standardized columns\n")

for file_path in excel_files:
    print(f"Processing: {file_path.name}")

    try:
        # Read only data sheet (skip metadata sheets)
        xl = pd.ExcelFile(file_path, engine='openpyxl')

        for sheet_name in xl.sheet_names:
            if ('description' in sheet_name.lower() or
                'field' in sheet_name.lower() or
                sheet_name in ['UpdateTime', 'Filler']):
                continue

            print(f"  Reading sheet: {sheet_name}...", end='', flush=True)
            df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
            print(f" {len(df)} rows")

            # Rename columns
            df.rename(columns=COLUMN_MAPPING, inplace=True)

            # Add missing columns
            if 'I_GROUP' not in df.columns:
                df['I_GROUP'] = 'cross-industry'
            if 'PRIM_STATE' not in df.columns:
                df['PRIM_STATE'] = None
            if 'PCT_RPT' not in df.columns:
                df['PCT_RPT'] = None

            # Extract year from filename
            import re
            year_match = re.search(r'20\d{2}', file_path.stem)
            year = year_match.group() if year_match else 'unknown'

            # Save as CSV
            csv_path = csv_dir / f"oews_{year}.csv"
            print(f"  Saving to: {csv_path.name}...", end='', flush=True)
            df.to_csv(csv_path, index=False)

            # Check file sizes
            excel_mb = file_path.stat().st_size / 1024 / 1024
            csv_mb = csv_path.stat().st_size / 1024 / 1024
            print(f" done! ({excel_mb:.1f}MB → {csv_mb:.1f}MB)")

    except Exception as e:
        print(f"  ERROR: {e}")

print(f"\n✓ CSV files saved to: {csv_dir}/")
print("\nNow we can migrate from CSV files which is MUCH faster!")
