"""Standardize column names across all OEWS Excel files - simplified version"""
import pandas as pd
from pathlib import Path
import shutil

# Column name mapping
COLUMN_MAPPING = {
    # Area columns (handle both cases)
    'area': 'AREA', 'AREA': 'AREA',
    'area_title': 'AREA_TITLE', 'AREA_TITLE': 'AREA_TITLE',
    'area_type': 'AREA_TYPE', 'AREA_TYPE': 'AREA_TYPE',

    # NAICS
    'naics': 'NAICS', 'NAICS': 'NAICS',
    'naics_title': 'NAICS_TITLE', 'NAICS_TITLE': 'NAICS_TITLE',

    # Ownership
    'own_code': 'OWN_CODE', 'OWN_CODE': 'OWN_CODE',

    # Occupation - handle space in "occ code"
    'occ code': 'OCC_CODE', 'occ_code': 'OCC_CODE', 'OCC_CODE': 'OCC_CODE',
    'occ title': 'OCC_TITLE', 'occ_title': 'OCC_TITLE', 'OCC_TITLE': 'OCC_TITLE',

    # Group columns - rename old GROUP to O_GROUP
    'group': 'O_GROUP', 'GROUP': 'O_GROUP',
    'o_group': 'O_GROUP', 'O_GROUP': 'O_GROUP',
    'i_group': 'I_GROUP', 'I_GROUP': 'I_GROUP',

    # Employment
    'tot_emp': 'TOT_EMP', 'TOT_EMP': 'TOT_EMP',
    'emp_prse': 'EMP_PRSE', 'EMP_PRSE': 'EMP_PRSE',

    # Jobs
    'jobs_1000': 'JOBS_1000', 'JOBS_1000': 'JOBS_1000',
    'jobs_1000_orig': 'JOBS_1000',  # 2019 variant

    # Location quotient
    'LOC_Q': 'LOC_QUOTIENT', 'loc_quotient': 'LOC_QUOTIENT', 'LOC_QUOTIENT': 'LOC_QUOTIENT',

    # Percent total
    'pct_tot': 'PCT_TOTAL', 'PCT_TOT': 'PCT_TOTAL',
    'pct_total': 'PCT_TOTAL', 'PCT_TOTAL': 'PCT_TOTAL',

    # Wages
    'h_mean': 'H_MEAN', 'H_MEAN': 'H_MEAN',
    'a_mean': 'A_MEAN', 'A_MEAN': 'A_MEAN',
    'mean_prse': 'MEAN_PRSE', 'MEAN_PRSE': 'MEAN_PRSE',

    # Percentiles
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

    # Flags
    'annual': 'ANNUAL', 'ANNUAL': 'ANNUAL',
    'hourly': 'HOURLY', 'HOURLY': 'HOURLY',

    # New columns
    'PRIM_STATE': 'PRIM_STATE',
    'PCT_RPT': 'PCT_RPT',
}

def standardize_file(file_path):
    """Standardize a single Excel file"""
    print(f"\n{'='*80}")
    print(f"Processing: {file_path.name}")
    print('='*80)

    try:
        xl = pd.ExcelFile(file_path, engine='openpyxl')
        temp_path = file_path.with_suffix('.xlsx.new')

        with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
            for sheet_name in xl.sheet_names:
                # Only process data sheets
                if ('description' in sheet_name.lower() or
                    'field' in sheet_name.lower() or
                    sheet_name in ['UpdateTime', 'Filler']):
                    print(f"  Skipping: {sheet_name}")
                    continue

                print(f"  Processing: {sheet_name}")

                # Read sheet
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                print(f"    Original: {len(df.columns)} columns, {len(df)} rows")

                # Rename columns
                df.rename(columns=COLUMN_MAPPING, inplace=True)

                # Add missing columns
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
                    print(f"    Added: {', '.join(added)}")

                # Save
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"    Saved: {len(df.columns)} columns, {len(df)} rows")

        # Replace original with new file
        file_path.unlink()
        temp_path.rename(file_path)
        print(f"  ✓ SUCCESS")
        return True

    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

# Main
if __name__ == '__main__':
    data_dir = Path('data')
    excel_files = sorted([f for f in data_dir.glob('*.xlsx') if not f.name.endswith('.backup')])

    print(f"Found {len(excel_files)} files to process\n")

    success = 0
    for file_path in excel_files:
        if standardize_file(file_path):
            success += 1

    print(f"\n{'='*80}")
    print(f"SUMMARY: {success}/{len(excel_files)} files standardized")
    print('='*80)
