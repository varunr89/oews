"""Migrate standardized CSV files directly to SQLite database - FAST!"""
import pandas as pd
from pathlib import Path
import sqlite3
from datetime import datetime

# Database path
db_path = Path('data/oews.db')

# Remove old database
if db_path.exists():
    db_path.unlink()
    print(f"Removed old database: {db_path}")

# Connect to database
print(f"\nCreating new database: {db_path}")
conn = sqlite3.connect(db_path)

# Get all CSV files
csv_files = sorted(Path('data').glob('*.csv'))
print(f"Found {len(csv_files)} CSV files to migrate\n")

total_rows = 0

for csv_file in csv_files:
    print(f"{'='*80}")
    print(f"Migrating: {csv_file.name}")
    print(f"{'='*80}")

    try:
        # Read CSV
        print(f"  Reading CSV...", end='', flush=True)
        df = pd.read_csv(csv_file, low_memory=False)
        print(f" {len(df):,} rows, {len(df.columns)} columns")

        # Add source tracking columns
        df['_source_file'] = csv_file.name
        df['_imported_at'] = datetime.now()

        # Extract year from filename for tracking
        import re
        year_match = re.search(r'20\d{2}', csv_file.stem)
        df['_data_year'] = int(year_match.group()) if year_match else None

        print(f"  Writing to database...", end='', flush=True)

        # Append to database (creates table on first write)
        df.to_sql(
            'oews_data',
            conn,
            if_exists='append',  # Append to existing table
            index=False,
            chunksize=10000  # Write in chunks for better performance
        )

        print(f" done!")
        total_rows += len(df)

        # Show progress
        current_count = pd.read_sql_query("SELECT COUNT(*) as count FROM oews_data", conn).iloc[0]['count']
        print(f"  Total rows in database: {current_count:,}")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()

# Final summary
print(f"\n{'='*80}")
print("MIGRATION COMPLETE")
print(f"{'='*80}")

# Get statistics
stats = pd.read_sql_query("""
    SELECT
        COUNT(*) as total_rows,
        COUNT(DISTINCT _source_file) as files,
        COUNT(DISTINCT _data_year) as years,
        MIN(_data_year) as min_year,
        MAX(_data_year) as max_year
    FROM oews_data
""", conn)

print(f"\nDatabase: {db_path}")
print(f"Total rows: {stats.iloc[0]['total_rows']:,}")
print(f"Source files: {stats.iloc[0]['files']}")
print(f"Year range: {stats.iloc[0]['min_year']} - {stats.iloc[0]['max_year']}")

# Show database size
db_size_mb = db_path.stat().st_size / 1024 / 1024
print(f"Database size: {db_size_mb:.1f} MB")

# Close connection
conn.close()

print("\n✓ Migration complete!")
print(f"\nYou can now query the database:")
print(f"  sqlite3 {db_path}")
print(f"  SELECT COUNT(*) FROM oews_data;")
