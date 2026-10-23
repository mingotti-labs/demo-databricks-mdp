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
# Also drops ingested_timestamp, which changes on every row at every load: it
# must stay out of the snapshot (bronze full pattern, openspec
# rollout-bronze-full-pattern; see country_codes_scd2.py). Full-row duplicates
# share their ingested_timestamp, so dropping it after dropDuplicates changes
# nothing about which rows are kept.
from pyspark import pipelines as dp

KEY_COLUMNS = ["subdivision_code", "language_code", "subdivision_name"]


@dp.materialized_view(private=True)
def subdivision_codes_deduped():
    deduped = spark.read.table("bronze_iso.subdivision_codes_raw").dropDuplicates(
        KEY_COLUMNS
    )
    return deduped.drop("ingested_timestamp")
