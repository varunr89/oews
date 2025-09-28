"""
Excel to database loading pipeline for OEWS data.
"""

import logging
import pandas as pd
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm

from config.constants import (
    EXCEL_COLUMN_MAPPING,
    SUPPRESSED_DATA_INDICATORS,
    FILE_PATTERNS,
    VALIDATION_RULES
)
from config.settings import Settings
from .connection import DatabaseManager
from .models import (
    GeographicArea, Occupation, Industry, OwnershipType,
    EmploymentWageData, DataVintage
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OEWSDataLoader:
    """Loads OEWS data from Excel files into the database."""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.settings = Settings()
        self.stats = {
            "files_processed": 0,
            "total_records": 0,
            "skipped_records": 0,
            "dimension_records": {
                "areas": 0,
                "occupations": 0,
                "industries": 0
            }
        }

    def load_all_files(self) -> Dict:
        """Load all Excel files from the data directory."""
        data_files = self.settings.get_data_files()
        logger.info(f"Found {len(data_files)} data files to process")

        for file_path in data_files:
            try:
                self.load_file(file_path)
                self.stats["files_processed"] += 1
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")

        logger.info(f"Loading complete. Stats: {self.stats}")
        return self.stats

    def load_file(self, file_path: str):
        """Load a single Excel file into the database."""
        file_name = Path(file_path).name
        logger.info(f"Loading file: {file_name}")

        # Extract survey year from filename
        survey_year = self._extract_survey_year(file_name)
        if not survey_year:
            logger.warning(f"Could not extract survey year from {file_name}")
            return

        # Check if file already loaded
        if self._is_file_already_loaded(file_name):
            logger.info(f"File {file_name} already loaded, skipping")
            return

        # Read Excel file
        df = self._read_excel_file(file_path)
        if df is None or df.empty:
            logger.warning(f"No data found in {file_name}")
            return

        # Process the data
        processed_df = self._process_dataframe(df, survey_year)
        if processed_df.empty:
            logger.warning(f"No valid data after processing {file_name}")
            return

        # Load dimension data first
        self._load_dimension_data(processed_df)

        # Load fact data
        records_loaded = self._load_fact_data(processed_df, survey_year)

        # Record the file as loaded
        self._record_file_loaded(file_name, survey_year, records_loaded)

        logger.info(f"Successfully loaded {records_loaded} records from {file_name}")
        self.stats["total_records"] += records_loaded

    def _read_excel_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """Read Excel file and return the main data sheet."""
        try:
            # Read the Excel file to find the main data sheet
            excel_file = pd.ExcelFile(file_path)

            # Look for the main data sheet (usually the first one with 'data' in name)
            data_sheet = None
            for sheet_name in excel_file.sheet_names:
                if any(keyword in sheet_name.lower() for keyword in ['data', 'may', 'all']):
                    data_sheet = sheet_name
                    break

            if not data_sheet:
                data_sheet = excel_file.sheet_names[0]  # Use first sheet as fallback

            df = pd.read_excel(file_path, sheet_name=data_sheet)
            logger.info(f"Read {len(df)} rows from sheet '{data_sheet}'")
            return df

        except Exception as e:
            logger.error(f"Error reading Excel file {file_path}: {e}")
            return None

    def _process_dataframe(self, df: pd.DataFrame, survey_year: int) -> pd.DataFrame:
        """Process and clean the DataFrame."""
        # Rename columns to match our schema
        df_renamed = df.rename(columns=EXCEL_COLUMN_MAPPING)

        # Add survey year
        df_renamed['survey_year'] = survey_year
        df_renamed['survey_month'] = 'May'

        # Clean suppressed data indicators
        df_cleaned = self._clean_suppressed_data(df_renamed)

        # Validate and filter data
        df_valid = self._validate_data(df_cleaned)

        return df_valid

    def _clean_suppressed_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Replace suppressed data indicators with None."""
        df_copy = df.copy()

        # Replace suppressed indicators with None for numeric columns
        numeric_columns = [
            'total_employment', 'employment_prse', 'jobs_per_1000', 'location_quotient',
            'mean_hourly_wage', 'mean_annual_wage', 'wage_prse',
            'hourly_10th_pct', 'hourly_25th_pct', 'hourly_median', 'hourly_75th_pct', 'hourly_90th_pct',
            'annual_10th_pct', 'annual_25th_pct', 'annual_median', 'annual_75th_pct', 'annual_90th_pct'
        ]

        for col in numeric_columns:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].replace(SUPPRESSED_DATA_INDICATORS, None)
                df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')

        # Handle boolean columns
        boolean_columns = ['annual_only', 'hourly_only']
        for col in boolean_columns:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].map({'TRUE': True}).fillna(False)

        return df_copy

    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate data according to business rules."""
        initial_count = len(df)

        # Remove rows with missing required fields
        required_fields = ['area_code', 'occ_code', 'naics_code', 'own_code']
        df_valid = df.dropna(subset=required_fields)

        # Remove rows with invalid area/occ codes (convert to string first)
        df_valid['area_code'] = df_valid['area_code'].astype(str)
        df_valid['occ_code'] = df_valid['occ_code'].astype(str)
        df_valid['naics_code'] = df_valid['naics_code'].astype(str)

        df_valid = df_valid[
            (df_valid['area_code'].str.len() <= 10) &
            (df_valid['occ_code'].str.len() <= 10) &
            (df_valid['naics_code'].str.len() <= 10)
        ]

        skipped = initial_count - len(df_valid)
        if skipped > 0:
            logger.info(f"Skipped {skipped} invalid records")
            self.stats["skipped_records"] += skipped

        return df_valid

    def _load_dimension_data(self, df: pd.DataFrame):
        """Load dimension table data (areas, occupations, industries)."""
        # Load each dimension table separately to handle errors better
        self._load_areas(df)
        self._load_occupations(df)
        self._load_industries(df)

    def _load_areas(self, df: pd.DataFrame):
        """Load geographic areas dimension data."""
        areas_data = df[['area_code', 'area_title', 'area_type', 'primary_state']].drop_duplicates()

        with self.db_manager.get_session() as session:
            for _, row in areas_data.iterrows():
                existing = session.query(GeographicArea).filter_by(area_code=row['area_code']).first()
                if not existing:
                    area = GeographicArea(
                        area_code=row['area_code'],
                        area_title=row['area_title'],
                        area_type=row['area_type'],
                        primary_state=row['primary_state']
                    )
                    session.add(area)
                    self.stats["dimension_records"]["areas"] += 1

    def _load_occupations(self, df: pd.DataFrame):
        """Load occupations dimension data."""
        occs_data = df[['occ_code', 'occ_title', 'o_group']].drop_duplicates()

        with self.db_manager.get_session() as session:
            for _, row in occs_data.iterrows():
                existing = session.query(Occupation).filter_by(occ_code=row['occ_code']).first()
                if not existing:
                    occupation = Occupation(
                        occ_code=row['occ_code'],
                        occ_title=row['occ_title'],
                        o_group=row['o_group']
                    )
                    session.add(occupation)
                    self.stats["dimension_records"]["occupations"] += 1

    def _load_industries(self, df: pd.DataFrame):
        """Load industries dimension data."""
        industries_data = df[['naics_code', 'naics_title', 'i_group']].drop_duplicates()

        with self.db_manager.get_session() as session:
            for _, row in industries_data.iterrows():
                existing = session.query(Industry).filter_by(naics_code=row['naics_code']).first()
                if not existing:
                    industry = Industry(
                        naics_code=row['naics_code'],
                        naics_title=row['naics_title'],
                        i_group=row['i_group']
                    )
                    session.add(industry)
                    self.stats["dimension_records"]["industries"] += 1

    def _load_fact_data(self, df: pd.DataFrame, survey_year: int) -> int:
        """Load fact table data in batches."""
        batch_size = 1000
        total_records = len(df)
        records_loaded = 0

        with self.db_manager.get_session() as session:
            for i in tqdm(range(0, total_records, batch_size), desc="Loading employment data"):
                batch_df = df.iloc[i:i + batch_size]

                for _, row in batch_df.iterrows():
                    employment_data = EmploymentWageData(
                        area_code=row['area_code'],
                        occ_code=row['occ_code'],
                        naics_code=row['naics_code'],
                        own_code=row['own_code'],
                        survey_year=survey_year,
                        survey_month=row.get('survey_month', 'May'),
                        total_employment=row.get('total_employment'),
                        employment_prse=row.get('employment_prse'),
                        jobs_per_1000=row.get('jobs_per_1000'),
                        location_quotient=row.get('location_quotient'),
                        pct_total=row.get('pct_total'),
                        pct_reporting=row.get('pct_reporting'),
                        mean_hourly_wage=row.get('mean_hourly_wage'),
                        mean_annual_wage=row.get('mean_annual_wage'),
                        wage_prse=row.get('wage_prse'),
                        hourly_10th_pct=row.get('hourly_10th_pct'),
                        hourly_25th_pct=row.get('hourly_25th_pct'),
                        hourly_median=row.get('hourly_median'),
                        hourly_75th_pct=row.get('hourly_75th_pct'),
                        hourly_90th_pct=row.get('hourly_90th_pct'),
                        annual_10th_pct=row.get('annual_10th_pct'),
                        annual_25th_pct=row.get('annual_25th_pct'),
                        annual_median=row.get('annual_median'),
                        annual_75th_pct=row.get('annual_75th_pct'),
                        annual_90th_pct=row.get('annual_90th_pct'),
                        annual_only=row.get('annual_only', False),
                        hourly_only=row.get('hourly_only', False)
                    )
                    session.add(employment_data)
                    records_loaded += 1

        return records_loaded

    def _extract_survey_year(self, file_name: str) -> Optional[int]:
        """Extract survey year from filename."""
        pattern = FILE_PATTERNS["survey_year_extract"]
        match = re.search(pattern, file_name)
        if match:
            return int(match.group(1))
        return None

    def _is_file_already_loaded(self, file_name: str) -> bool:
        """Check if file has already been loaded."""
        with self.db_manager.get_session() as session:
            return session.query(DataVintage).filter_by(file_name=file_name).first() is not None

    def _record_file_loaded(self, file_name: str, survey_year: int, total_records: int):
        """Record that a file has been loaded."""
        with self.db_manager.get_session() as session:
            vintage = DataVintage(
                file_name=file_name,
                survey_year=survey_year,
                survey_month="May",
                total_records=total_records
            )
            session.add(vintage)

# Global loader instance
data_loader = OEWSDataLoader()