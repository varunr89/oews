"""Centralized OEWS schema metadata used across CLI commands."""

from __future__ import annotations

from typing import Dict, List, Optional

try:  # pragma: no cover - optional dependency import guard
    import polars as pl
except ImportError:  # pragma: no cover - handled by CLI validation
    pl = None  # type: ignore[assignment]

CANONICAL_COLUMNS: List[str] = [
    "AREA",
    "AREA_TITLE",
    "AREA_TYPE",
    "PRIM_STATE",
    "NAICS",
    "NAICS_TITLE",
    "I_GROUP",
    "OWN_CODE",
    "OCC_CODE",
    "OCC_TITLE",
    "O_GROUP",
    "TOT_EMP",
    "EMP_PRSE",
    "JOBS_1000",
    "LOC_QUOTIENT",
    "PCT_TOTAL",
    "PCT_RPT",
    "H_MEAN",
    "A_MEAN",
    "MEAN_PRSE",
    "H_PCT10",
    "H_PCT25",
    "H_MEDIAN",
    "H_PCT75",
    "H_PCT90",
    "A_PCT10",
    "A_PCT25",
    "A_MEDIAN",
    "A_PCT75",
    "A_PCT90",
    "ANNUAL",
    "HOURLY",
]

COLUMN_CANONICAL_MAP: Dict[str, str] = {
    "area": "AREA",
    "area_title": "AREA_TITLE",
    "area_type": "AREA_TYPE",
    "prim_state": "PRIM_STATE",
    "primary_state": "PRIM_STATE",
    "naics": "NAICS",
    "naic": "NAICS",
    "naics_title": "NAICS_TITLE",
    "own_code": "OWN_CODE",
    "ownership_code": "OWN_CODE",
    "occ_code": "OCC_CODE",
    "occ_code1": "OCC_CODE",
    "occcode": "OCC_CODE",
    "occ_title": "OCC_TITLE",
    "occtitle": "OCC_TITLE",
    "o_group": "O_GROUP",
    "group": "O_GROUP",
    "i_group": "I_GROUP",
    "igroup": "I_GROUP",
    "tot_emp": "TOT_EMP",
    "total_emp": "TOT_EMP",
    "emp_prse": "EMP_PRSE",
    "jobs_1000": "JOBS_1000",
    "jobs_1000_orig": "JOBS_1000",
    "jobs_per_1000": "JOBS_1000",
    "loc_quotient": "LOC_QUOTIENT",
    "loc_quotiont": "LOC_QUOTIENT",
    "loc_q": "LOC_QUOTIENT",
    "pct_total": "PCT_TOTAL",
    "pct_tot": "PCT_TOTAL",
    "pcttotal": "PCT_TOTAL",
    "pct_rpt": "PCT_RPT",
    "percent_reporting": "PCT_RPT",
    "h_mean": "H_MEAN",
    "hourly_mean": "H_MEAN",
    "a_mean": "A_MEAN",
    "annual_mean": "A_MEAN",
    "mean_prse": "MEAN_PRSE",
    "h_pct10": "H_PCT10",
    "h_pct25": "H_PCT25",
    "h_median": "H_MEDIAN",
    "h_pct75": "H_PCT75",
    "h_pct90": "H_PCT90",
    "a_pct10": "A_PCT10",
    "a_pct25": "A_PCT25",
    "a_median": "A_MEDIAN",
    "a_pct75": "A_PCT75",
    "a_pct90": "A_PCT90",
    "annual": "ANNUAL",
    "hourly": "HOURLY",
}

COLUMN_DEFAULTS: Dict[str, Optional[str]] = {
    "I_GROUP": "cross-industry",
    "PRIM_STATE": None,
    "PCT_RPT": None,
}

if pl is not None:
    POLARS_NUMERIC_TYPES: Dict[str, "pl.DataType"] = {
        "AREA_TYPE": pl.Int16,
        "TOT_EMP": pl.Int64,
        "EMP_PRSE": pl.Float64,
        "JOBS_1000": pl.Float64,
        "LOC_QUOTIENT": pl.Float64,
        "PCT_TOTAL": pl.Float64,
        "PCT_RPT": pl.Float64,
        "H_MEAN": pl.Float64,
        "A_MEAN": pl.Float64,
        "MEAN_PRSE": pl.Float64,
        "H_PCT10": pl.Float64,
        "H_PCT25": pl.Float64,
        "H_MEDIAN": pl.Float64,
        "H_PCT75": pl.Float64,
        "H_PCT90": pl.Float64,
        "A_PCT10": pl.Float64,
        "A_PCT25": pl.Float64,
        "A_MEDIAN": pl.Float64,
        "A_PCT75": pl.Float64,
        "A_PCT90": pl.Float64,
    }
else:  # pragma: no cover - defensive default when polars absent
    POLARS_NUMERIC_TYPES = {}

METADATA_COLUMNS: List[str] = ["_source_file", "_source_folder", "_data_year"]
DB_EXTRA_COLUMNS: List[str] = ["SURVEY_YEAR", "SURVEY_MONTH", "SOURCE_FILE", "SOURCE_FOLDER"]

SCHEMA_VERSION = "2025.10"

__all__ = [
    "CANONICAL_COLUMNS",
    "COLUMN_CANONICAL_MAP",
    "COLUMN_DEFAULTS",
    "POLARS_NUMERIC_TYPES",
    "METADATA_COLUMNS",
    "DB_EXTRA_COLUMNS",
    "SCHEMA_VERSION",
]
