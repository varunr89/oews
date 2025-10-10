"""Check GROUP, I_GROUP, and O_GROUP column values"""
import pandas as pd
from pathlib import Path

# Check files with different GROUP configurations
files_to_check = [
    ('data/oes_data_2011.xlsx', 'oes_data_2011'),  # Has GROUP
    ('data/all_data_M_2016.xlsx', 'All May 2016 Data'),  # Has group
    ('data/all_data_M_2018.xlsx', 'All May 2018 Data'),  # Has i_group, o_group
    ('data/all_data_M_2024.xlsx', 'All May 2024 data'),  # Has I_GROUP, O_GROUP
]

for file_path, sheet_name in files_to_check:
    print(f"\n{'='*80}")
    print(f"File: {file_path}")
    print(f"Sheet: {sheet_name}")
    print('='*80)

    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=100)

        # Check which group columns exist
        group_cols = [col for col in df.columns if 'group' in col.lower()]
        print(f"\nGroup columns found: {group_cols}")

        for col in group_cols:
            print(f"\n{col} - Sample values (unique):")
            unique_vals = df[col].dropna().unique()[:10]
            for val in unique_vals:
                print(f"  - {val}")

            # Count null vs non-null
            total = len(df)
            non_null = df[col].notna().sum()
            null_count = df[col].isna().sum()
            print(f"\n{col} - Stats:")
            print(f"  Total rows: {total}")
            print(f"  Non-null: {non_null} ({non_null/total*100:.1f}%)")
            print(f"  Null: {null_count} ({null_count/total*100:.1f}%)")

    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
