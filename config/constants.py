"""
Constants and mappings for OEWS data processing.
"""

# Ownership type mappings
OWNERSHIP_TYPES = {
    1: "Federal Government",
    2: "State Government",
    3: "Local Government",
    5: "Private",
    35: "Private and Local Government",
    57: "Private, Local Government Gambling Establishments, and Local Government Casino Hotels",
    58: "Private plus State and Local Government Hospitals",
    59: "Private and Postal Service",
    123: "Federal, State, and Local Government",
    235: "Private, State, and Local Government",
    1235: "Federal, State, and Local Government and Private Sector"
}

# Area type mappings
AREA_TYPES = {
    1: "U.S.",
    2: "State",
    3: "U.S. Territory",
    4: "Metropolitan Statistical Area (MSA)",
    6: "Nonmetropolitan Area"
}

# Occupation group hierarchy
OCCUPATION_GROUPS = {
    "total": "All Occupations",
    "major": "Major Group",
    "minor": "Minor Group",
    "broad": "Broad Occupation",
    "detailed": "Detailed Occupation"
}

# Industry group hierarchy
INDUSTRY_GROUPS = {
    "cross-industry": "Cross-Industry",
    "sector": "NAICS Sector",
    "3-digit": "3-Digit NAICS",
    "4-digit": "4-Digit NAICS",
    "5-digit": "5-Digit NAICS",
    "6-digit": "6-Digit NAICS"
}

# Data quality indicators
SUPPRESSED_DATA_INDICATORS = ["*", "#", "**"]

# Wage percentiles for analysis
WAGE_PERCENTILES = [10, 25, 50, 75, 90]

# Employment metrics
EMPLOYMENT_METRICS = [
    "total_employment",
    "employment_prse",
    "jobs_per_1000",
    "location_quotient"
]

# Wage metrics
WAGE_METRICS = [
    "mean_hourly_wage",
    "mean_annual_wage",
    "hourly_10th_pct",
    "hourly_25th_pct",
    "hourly_median",
    "hourly_75th_pct",
    "hourly_90th_pct",
    "annual_10th_pct",
    "annual_25th_pct",
    "annual_median",
    "annual_75th_pct",
    "annual_90th_pct"
]

# Excel column mappings for OEWS data
EXCEL_COLUMN_MAPPING = {
    "AREA": "area_code",
    "AREA_TITLE": "area_title",
    "AREA_TYPE": "area_type",
    "PRIM_STATE": "primary_state",
    "NAICS": "naics_code",
    "NAICS_TITLE": "naics_title",
    "I_GROUP": "i_group",
    "OWN_CODE": "own_code",
    "OCC_CODE": "occ_code",
    "OCC_TITLE": "occ_title",
    "O_GROUP": "o_group",
    "TOT_EMP": "total_employment",
    "EMP_PRSE": "employment_prse",
    "JOBS_1000": "jobs_per_1000",
    "LOC_QUOTIENT": "location_quotient",
    "PCT_TOTAL": "pct_total",
    "PCT_RPT": "pct_reporting",
    "H_MEAN": "mean_hourly_wage",
    "A_MEAN": "mean_annual_wage",
    "MEAN_PRSE": "wage_prse",
    "H_PCT10": "hourly_10th_pct",
    "H_PCT25": "hourly_25th_pct",
    "H_MEDIAN": "hourly_median",
    "H_PCT75": "hourly_75th_pct",
    "H_PCT90": "hourly_90th_pct",
    "A_PCT10": "annual_10th_pct",
    "A_PCT25": "annual_25th_pct",
    "A_MEDIAN": "annual_median",
    "A_PCT75": "annual_75th_pct",
    "A_PCT90": "annual_90th_pct",
    "ANNUAL": "annual_only",
    "HOURLY": "hourly_only"
}

# File naming patterns
FILE_PATTERNS = {
    "oews_data": r"(all_data_M_|oes_data_|all_oes_data_)(\d{4})\.xlsx",
    "survey_year_extract": r"(\d{4})"
}

# Data validation rules
VALIDATION_RULES = {
    "area_code": {"type": str, "max_length": 10},
    "occ_code": {"type": str, "max_length": 10},
    "naics_code": {"type": str, "max_length": 10},
    "total_employment": {"type": int, "min_value": 0},
    "mean_annual_wage": {"type": int, "min_value": 0},
    "employment_prse": {"type": float, "min_value": 0, "max_value": 100}
}