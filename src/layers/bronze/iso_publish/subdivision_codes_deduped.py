# Private intermediate: dedupes bronze_iso.subdivision_codes_raw on the SCD
# key (subdivision_code, language_code, subdivision_name) before it reaches
# Auto CDC.
#
# Confirmed via a real pipeline run, not assumed: even with all three key
# columns, the source CSV has 10 genuine full-row duplicates (e.g.
# RU-DA/ru/Dagestan appears twice, byte-identical) --
# create_auto_cdc_from_snapshot_flow's DUPLICATE_KEY_VIOLATION rejects a
# source with more than one row per key outright, with zero tolerance for
# identical duplicates. `dropDuplicates` on the key here doesn't discard
# information -- verified locally that every group sharing a key has
# identical values in every other column too.
#
# This is real filtering work, not the unnecessary snapshot-wrapper
# anti-pattern phase3b-scd-snapshot-cleanup removed project-wide -- same
# justification as ACNC's charity_register_valid private view. The extra
# copies aren't silently discarded -- see subdivision_codes_quarantine.py
# (bronze_iso, complementary filter over the same raw table) for where
# they're kept visible: `raw = deduped + quarantine` exactly.
#
# Also stamps transformed_timestamp (publish layer) here, since this is
# the dataset that directly feeds Auto CDC -- same role
# market_summary_transformed plays in AirROI's pattern. dropDuplicates()
# runs before the timestamp column is added, so it dedupes on the same
# key regardless of run time.
from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp

KEY_COLUMNS = ["subdivision_code", "language_code", "subdivision_name"]


@dp.materialized_view(private=True)
def subdivision_codes_deduped():
    deduped = spark.read.table("bronze_iso.subdivision_codes_raw").dropDuplicates(KEY_COLUMNS)
    return deduped.withColumn("transformed_timestamp", current_timestamp())
