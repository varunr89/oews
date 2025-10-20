def test_schema_module_exports_expected_constants():
    from src import oews_schema  # noqa: PLC0415

    assert hasattr(oews_schema, "CANONICAL_COLUMNS")
    assert hasattr(oews_schema, "COLUMN_DEFAULTS")
    assert hasattr(oews_schema, "POLARS_NUMERIC_TYPES")
    assert len(oews_schema.CANONICAL_COLUMNS) > 0


def test_standardize_and_migrate_share_schema_objects():
    from src import oews_schema  # noqa: PLC0415
    from src.cli.scripts import migrate_csv_to_db, standardize_csv_columns  # noqa: PLC0415

    assert migrate_csv_to_db.CANONICAL_COLUMNS is oews_schema.CANONICAL_COLUMNS
    assert standardize_csv_columns.CANONICAL_COLUMNS is oews_schema.CANONICAL_COLUMNS
    assert migrate_csv_to_db.METADATA_COLUMNS == standardize_csv_columns.METADATA_COLUMNS
