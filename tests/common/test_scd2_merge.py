from common.scd2_merge import business_columns, merge_sql

COLUMNS = ["ABN", "name", "state", "ingested_timestamp", "transformed_timestamp"]


def test_business_columns_exclude_keys_platform_and_validity():
    assert business_columns(COLUMNS + ["__START_AT", "__END_AT"], ["ABN"]) == [
        "name",
        "state",
    ]


def test_change_check_is_null_safe_on_every_business_column():
    sql = merge_sql("c.s.t", "c.s.src", ["ABN"], COLUMNS)
    assert "t.`name` <=> s.`name` AND t.`state` <=> s.`state`" in sql
    assert "!=" not in sql


def test_only_written_rows_are_stamped():
    sql = merge_sql("c.s.t", "c.s.src", ["ABN"], COLUMNS)
    assert "WHEN MATCHED AND NOT (" in sql
    assert "WHEN NOT MATCHED BY SOURCE AND t.__END_AT IS NULL" in sql
    assert "s.ingested_timestamp, current_timestamp(), current_timestamp(), NULL" in sql
