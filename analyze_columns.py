"""Analyze column names across all OEWS Excel files"""
import pandas as pd
from pathlib import Path
import json

data_dir = Path('data')
excel_files = sorted(data_dir.glob('*.xlsx'))

results = {}

for file in excel_files:
    print(f"Reading {file.name}...")
    try:
        # Read only the first row to get column names
        xl = pd.ExcelFile(file, engine='openpyxl')

        file_info = {}
        for sheet_name in xl.sheet_names:
            # Skip description/metadata sheets
            if 'description' in sheet_name.lower() or 'field' in sheet_name.lower():
                continue

            df = pd.read_excel(file, sheet_name=sheet_name, nrows=0, engine='openpyxl')
            columns = df.columns.tolist()
            file_info[sheet_name] = columns
            print(f"  {sheet_name}: {len(columns)} columns")

        results[file.name] = file_info
    except Exception as e:
        print(f"  ERROR: {e}")

# Save results
with open('column_analysis.json', 'w') as f:
    json.dump(results, f, indent=2)

# Collect all unique column names
all_columns = set()
for file_data in results.values():
    for columns in file_data.values():
        all_columns.update(columns)

print(f"\nTotal unique column names: {len(all_columns)}")
print("\nAll unique columns:")
for col in sorted(all_columns):
    print(f"  - {col}")

# Save unique columns
with open('unique_columns.txt', 'w') as f:
    for col in sorted(all_columns):
        f.write(f"{col}\n")

print("\nResults saved to column_analysis.json and unique_columns.txt")
