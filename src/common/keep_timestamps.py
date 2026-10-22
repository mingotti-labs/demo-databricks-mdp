"""Full rebuild that keeps `transformed_timestamp` on unchanged rows.

A rebuilt row identical to a row of the previous table (every column but
`transformed_timestamp`, nulls equal) keeps that row's `transformed_timestamp`;
a new or changed row gets `current_timestamp()`. Rows that are gone disappear
with the overwrite.
"""

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import MapType

STAMP = "transformed_timestamp"


def compared_columns(columns: list[str]) -> list[str]:
    """Columns that decide whether a row is unchanged."""
    return [c for c in columns if c != STAMP]


def _comparable(df: DataFrame, alias: str, name: str) -> Column:
    column = F.col(f"{alias}.`{name}`")
    return F.to_json(column) if isinstance(df.schema[name].dataType, MapType) else column


def keep_timestamps(new: DataFrame, previous: DataFrame | None) -> DataFrame:
    """`new` with each row's `transformed_timestamp` kept or stamped now."""
    new = new.drop(STAMP)
    if previous is None:
        return new.withColumn(STAMP, F.current_timestamp())
    compared = compared_columns(new.columns)
    condition = [
        _comparable(new, "n", c).eqNullSafe(_comparable(previous, "o", c))
        for c in compared
    ]
    kept = previous.select(*compared, F.col(STAMP).alias("_kept"))
    return (
        new.alias("n")
        .join(kept.alias("o"), condition, "left")
        .select("n.*", F.coalesce(F.col("o._kept"), F.current_timestamp()).alias(STAMP))
    )
