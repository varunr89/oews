"""Standardize column names in CSV files - FAST"""
import pandas as pd
from pathlib import Path

# Column mapping - maps any variant to standard UPPERCASE name
COLUMN_MAPPING = {
    'area': 'AREA', 'AREA': 'AREA',
    'area_title': 'AREA_TITLE', 'AREA_TITLE': 'AREA_TITLE',
    'area_type': 'AREA_TYPE', 'AREA_TYPE': 'AREA_TYPE',
    'naics': 'NAICS', 'NAICS': 'NAICS',
    'naics_title': 'NAICS_TITLE', 'NAICS_TITLE': 'NAICS_TITLE',
    'own_code': 'OWN_CODE', 'OWN_CODE': 'OWN_CODE',
    'occ code': 'OCC_CODE',  # Space variant
    'occ_code': 'OCC_CODE', 'OCC_CODE': 'OCC_CODE',
    'occ title': 'OCC_TITLE',  # Space variant
    'occ_title': 'OCC_TITLE', 'OCC_TITLE': 'OCC_TITLE',
    'group': 'O_GROUP', 'GROUP': 'O_GROUP',  # Rename to O_GROUP
    'o_group': 'O_GROUP', 'O_GROUP': 'O_GROUP',
    'i_group': 'I_GROUP', 'I_GROUP': 'I_GROUP',
    'tot_emp': 'TOT_EMP', 'TOT_EMP': 'TOT_EMP',
    'emp_prse': 'EMP_PRSE', 'EMP_PRSE': 'EMP_PRSE',
    'jobs_1000': 'JOBS_1000', 'JOBS_1000': 'JOBS_1000',
    'jobs_1000_orig': 'JOBS_1000',  # 2019 variant
    'LOC_Q': 'LOC_QUOTIENT',
    'loc_quotient': 'LOC_QUOTIENT', 'LOC_QUOTIENT': 'LOC_QUOTIENT',
    'pct_tot': 'PCT_TOTAL', 'PCT_TOT': 'PCT_TOTAL',  # Different variants
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

# Standard column order
STANDARD_COLUMNS = [
    'AREA', 'AREA_TITLE', 'AREA_TYPE', 'PRIM_STATE',
    'NAICS', 'NAICS_TITLE', 'I_GROUP', 'OWN_CODE',
    'OCC_CODE', 'OCC_TITLE', 'O_GROUP',
    'TOT_EMP', 'EMP_PRSE', 'JOBS_1000', 'LOC_QUOTIENT', 'PCT_TOTAL', 'PCT_RPT',
    'H_MEAN', 'A_MEAN', 'MEAN_PRSE',
    'H_PCT10', 'H_PCT25', 'H_MEDIAN', 'H_PCT75', 'H_PCT90',
    'A_PCT10', 'A_PCT25', 'A_MEDIAN', 'A_PCT75', 'A_PCT90',
    'ANNUAL', 'HOURLY'
]

data_dir = Path('data')
csv_files = sorted(data_dir.glob('*.csv'))

print(f"Standardizing {len(csv_files)} CSV files\n")

for csv_path in csv_files:
    print(f"Processing: {csv_path.name}")

    try:
        # Read CSV
        print(f"  Reading...", end='', flush=True)
        df = pd.read_csv(csv_path, low_memory=False)
        print(f" {len(df)} rows, {len(df.columns)} cols")

        # Show original columns
        print(f"  Original columns: {list(df.columns[:5])}...")

        # Rename columns
        df.rename(columns=COLUMN_MAPPING, inplace=True)

        # Add missing columns with defaults
        added = []
        if 'I_GROUP' not in df.columns:
            df['I_GROUP'] = 'cross-industry'
            added.append('I_GROUP')

        if 'PRIM_STATE' not in df.columns:
            df['PRIM_STATE'] = None
            added.append('PRIM_STATE')

        if 'PCT_RPT' not in df.columns:
            df['PCT_RPT'] = None
            added.append('PCT_RPT')

        if added:
            print(f"  Added columns: {', '.join(added)}")

        # Reorder columns to match standard order
        available_cols = [col for col in STANDARD_COLUMNS if col in df.columns]
        extra_cols = [col for col in df.columns if col not in STANDARD_COLUMNS]

        if extra_cols:
            print(f"  Warning: Extra columns: {extra_cols}")
            available_cols.extend(extra_cols)

        df = df[available_cols]

        # Save standardized CSV
        print(f"  Saving...", end='', flush=True)
        df.to_csv(csv_path, index=False)

        size_mb = csv_path.stat().st_size / 1024 / 1024
        print(f" done! ({size_mb:.1f}MB, {len(df.columns)} cols)")

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

print(f"\n✓ All CSV files standardized!")
print(f"\nStandard columns ({len(STANDARD_COLUMNS)}):")
print(", ".join(STANDARD_COLUMNS))
