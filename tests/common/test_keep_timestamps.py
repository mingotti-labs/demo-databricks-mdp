import pytest

pytest.importorskip("pyspark")

from common.keep_timestamps import compared_columns


def test_every_column_but_the_stamp_is_compared():
    assert compared_columns(["state", "row_count", "transformed_timestamp"]) == [
        "state",
        "row_count",
    ]
