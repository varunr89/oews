from src.database.schema import get_oews_schema_description, get_table_list

def test_get_table_list():
    """Test that table list is returned."""
    tables = get_table_list()
    assert 'oews_data' in tables
    assert isinstance(tables, list)

def test_get_oews_schema_description():
    """Test that schema description is returned for LLM."""
    schema = get_oews_schema_description('oews_data')
    assert 'AREA_TITLE' in schema
    assert 'OCC_TITLE' in schema
    assert 'A_MEDIAN' in schema
    assert isinstance(schema, str)
