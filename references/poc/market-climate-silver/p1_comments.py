"""Probe P1 (market-climate-silver): can a materialized view describe only some of its columns?

Two throwaway views in pattern_bronze:
- p1_partial: schema= lists one of the two columns, with a COMMENT
- p1_full: schema= lists both columns, each with a COMMENT
Run as a throwaway pipeline (see run.py); then DESCRIBE TABLE both.
"""

from pyspark import pipelines as dp


# p1_partial removed after the first run: a partial schema= was rejected (see p1_result.txt)


@dp.materialized_view(
    schema="amount DECIMAL(10, 2) COMMENT 'first column, described', label STRING COMMENT 'second column, described'"
)
def p1_full():
    return spark.sql("SELECT CAST(1.5 AS DECIMAL(10, 2)) AS amount, 'x' AS label")
