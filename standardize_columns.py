"""Standardize column names across all OEWS Excel files"""
import pandas as pd
from pathlib import Path
import shutil

# Column name mapping - maps any variant to the standard name
COLUMN_MAPPING = {
    # Area columns
    'area': 'AREA',
    'AREA': 'AREA',
    'area_title': 'AREA_TITLE',
    'AREA_TITLE': 'AREA_TITLE',
    'area_type': 'AREA_TYPE',
    'AREA_TYPE': 'AREA_TYPE',

    # NAICS columns
    'naics': 'NAICS',
    'NAICS': 'NAICS',
    'naics_title': 'NAICS_TITLE',
    'NAICS_TITLE': 'NAICS_TITLE',

    # Ownership
    'own_code': 'OWN_CODE',
    'OWN_CODE': 'OWN_CODE',

    # Occupation columns
    'occ code': 'OCC_CODE',
    'occ_code': 'OCC_CODE',
    'OCC_CODE': 'OCC_CODE',
    'occ title': 'OCC_TITLE',
    'occ_title': 'OCC_TITLE',
    'OCC_TITLE': 'OCC_TITLE',

    # Group columns - rename old GROUP to O_GROUP
    'group': 'O_GROUP',
    'GROUP': 'O_GROUP',
    'o_group': 'O_GROUP',
    'O_GROUP': 'O_GROUP',
    'i_group': 'I_GROUP',
    'I_GROUP': 'I_GROUP',

    # Employment columns
    'tot_emp': 'TOT_EMP',
    'TOT_EMP': 'TOT_EMP',
    'emp_prse': 'EMP_PRSE',
    'EMP_PRSE': 'EMP_PRSE',

    # Jobs columns
    'jobs_1000': 'JOBS_1000',
    'JOBS_1000': 'JOBS_1000',
    'jobs_1000_orig': 'JOBS_1000',  # 2019 variant

    # Location quotient
    'LOC_Q': 'LOC_QUOTIENT',
    'loc_quotient': 'LOC_QUOTIENT',
    'LOC_QUOTIENT': 'LOC_QUOTIENT',

    # Percent total
    'pct_tot': 'PCT_TOTAL',
    'PCT_TOT': 'PCT_TOTAL',
    'pct_total': 'PCT_TOTAL',
    'PCT_TOTAL': 'PCT_TOTAL',

    # Wage columns
    'h_mean': 'H_MEAN',
    'H_MEAN': 'H_MEAN',
    'a_mean': 'A_MEAN',
    'A_MEAN': 'A_MEAN',
    'mean_prse': 'MEAN_PRSE',
    'MEAN_PRSE': 'MEAN_PRSE',

    # Percentile columns
    'h_pct10': 'H_PCT10',
    'H_PCT10': 'H_PCT10',
    'h_pct25': 'H_PCT25',
    'H_PCT25': 'H_PCT25',
    'h_median': 'H_MEDIAN',
    'H_MEDIAN': 'H_MEDIAN',
    'h_pct75': 'H_PCT75',
    'H_PCT75': 'H_PCT75',
    'h_pct90': 'H_PCT90',
    'H_PCT90': 'H_PCT90',

    'a_pct10': 'A_PCT10',
    'A_PCT10': 'A_PCT10',
    'a_pct25': 'A_PCT25',
    'A_PCT25': 'A_PCT25',
    'a_median': 'A_MEDIAN',
    'A_MEDIAN': 'A_MEDIAN',
    'a_pct75': 'A_PCT75',
    'A_PCT75': 'A_PCT75',
    'a_pct90': 'A_PCT90',
    'A_PCT90': 'A_PCT90',

    # Annual/Hourly flags
    'annual': 'ANNUAL',
    'ANNUAL': 'ANNUAL',
    'hourly': 'HOURLY',
    'HOURLY': 'HOURLY',

    # New columns in later years
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

def standardize_file(file_path, backup=True):
    """Standardize column names in an Excel file"""
    print(f"\nProcessing: {file_path.name}")

    # Create temporary output file
    temp_path = file_path.with_suffix('.xlsx.temp')

    try:
        # Read the Excel file
        xl = pd.ExcelFile(file_path, engine='openpyxl')

        # Create a writer for the temporary output
        with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
            for sheet_name in xl.sheet_names:
                # Check if this is a data sheet or metadata sheet
                is_data_sheet = (
                    'description' not in sheet_name.lower() and
                    'field' not in sheet_name.lower() and
                    sheet_name not in ['UpdateTime', 'Filler']
                )

                if not is_data_sheet:
                    print(f"  Copying sheet as-is: {sheet_name}")
                    # Copy non-data sheets without modification
                    df_original = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                    df_original.to_excel(writer, sheet_name=sheet_name, index=False)
                    continue

                print(f"  Processing sheet: {sheet_name}")

                # Read the sheet
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')

                # Rename columns
                original_cols = df.columns.tolist()
                df.rename(columns=COLUMN_MAPPING, inplace=True)
                renamed_cols = df.columns.tolist()

                # Show what was renamed
                changes = []
                for old, new in zip(original_cols, renamed_cols):
                    if old != new:
                        changes.append(f"{old} → {new}")

                if changes:
                    print(f"    Renamed {len(changes)} columns:")
                    for change in changes[:5]:  # Show first 5
                        print(f"      {change}")
                    if len(changes) > 5:
                        print(f"      ... and {len(changes) - 5} more")

                # Add missing columns with defaults
                added_cols = []

                if 'I_GROUP' not in df.columns:
                    df['I_GROUP'] = 'cross-industry'
                    added_cols.append('I_GROUP')

                if 'PRIM_STATE' not in df.columns:
                    df['PRIM_STATE'] = None
                    added_cols.append('PRIM_STATE')

                if 'PCT_RPT' not in df.columns:
                    df['PCT_RPT'] = None
                    added_cols.append('PCT_RPT')

                if added_cols:
                    print(f"    Added columns: {', '.join(added_cols)}")

                # Reorder columns to match standard order
                available_cols = [col for col in STANDARD_COLUMNS if col in df.columns]
                extra_cols = [col for col in df.columns if col not in STANDARD_COLUMNS]

                if extra_cols:
                    print(f"    Warning: Extra columns not in standard list: {extra_cols}")
                    available_cols.extend(extra_cols)

                df = df[available_cols]

                # Write the standardized sheet
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"    ✓ Saved with {len(df.columns)} columns, {len(df)} rows")

        # Success - replace original with temp file
        if backup:
            backup_path = file_path.with_suffix('.xlsx.backup')
            if not backup_path.exists():
                shutil.copy2(file_path, backup_path)
                print(f"  Backup created: {backup_path.name}")

        shutil.move(temp_path, file_path)
        print(f"  ✓ File standardized successfully")
        return True

    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        return False

# Main execution
if __name__ == '__main__':
    data_dir = Path('data')
    excel_files = sorted(data_dir.glob('*.xlsx'))

    # Filter out backup files
    excel_files = [f for f in excel_files if not f.name.endswith('.backup')]

    print(f"Found {len(excel_files)} Excel files to process")
    print("="*80)

    success_count = 0
    for file_path in excel_files:
        if standardize_file(file_path, backup=True):
            success_count += 1

    print("\n" + "="*80)
    print(f"SUMMARY: {success_count}/{len(excel_files)} files standardized successfully")
    print("="*80)

    if success_count == len(excel_files):
        print("\n✓ All files standardized!")
        print("\nBackup files created with .xlsx.backup extension")
        print("You can delete backups once you verify the standardization worked correctly.")
    else:
        print(f"\n⚠ {len(excel_files) - success_count} files failed")
