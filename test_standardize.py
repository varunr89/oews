"""Test standardization on a single file"""
import pandas as pd
from pathlib import Path

file_path = Path('data/oes_data_2011.xlsx')
temp_path = Path('data/test_output.xlsx')

# Column mapping
COLUMN_MAPPING = {
    'AREA': 'AREA',
    'AREA_TITLE': 'AREA_TITLE',
    'AREA_TYPE': 'AREA_TYPE',
    'NAICS': 'NAICS',
    'NAICS_TITLE': 'NAICS_TITLE',
    'OWN_CODE': 'OWN_CODE',
    'OCC_CODE': 'OCC_CODE',
    'OCC_TITLE': 'OCC_TITLE',
    'GROUP': 'O_GROUP',  # Rename GROUP to O_GROUP
    'TOT_EMP': 'TOT_EMP',
    'EMP_PRSE': 'EMP_PRSE',
    'JOBS_1000': 'JOBS_1000',
    'LOC_Q': 'LOC_QUOTIENT',  # Rename LOC_Q to LOC_QUOTIENT
    'PCT_TOT': 'PCT_TOTAL',  # Rename PCT_TOT to PCT_TOTAL
    'H_MEAN': 'H_MEAN',
    'A_MEAN': 'A_MEAN',
    'MEAN_PRSE': 'MEAN_PRSE',
    'H_PCT10': 'H_PCT10',
    'H_PCT25': 'H_PCT25',
    'H_MEDIAN': 'H_MEDIAN',
    'H_PCT75': 'H_PCT75',
    'H_PCT90': 'H_PCT90',
    'A_PCT10': 'A_PCT10',
    'A_PCT25': 'A_PCT25',
    'A_MEDIAN': 'A_MEDIAN',
    'A_PCT75': 'A_PCT75',
    'A_PCT90': 'A_PCT90',
    'ANNUAL': 'ANNUAL',
    'HOURLY': 'HOURLY',
}

print("Reading file...")
df = pd.read_excel(file_path, sheet_name='oes_data_2011')

print(f"Original columns: {df.columns.tolist()}")

# Rename
df.rename(columns=COLUMN_MAPPING, inplace=True)

# Add I_GROUP
df['I_GROUP'] = 'cross-industry'
df['PRIM_STATE'] = None
df['PCT_RPT'] = None

print(f"New columns: {df.columns.tolist()}")
print(f"Rows: {len(df)}")

# Save
print("Saving...")
df.to_excel(temp_path, sheet_name='oes_data_2011', index=False, engine='openpyxl')

print(f"✓ Saved to {temp_path}")
print(f"File size: {temp_path.stat().st_size / 1024 / 1024:.1f} MB")
