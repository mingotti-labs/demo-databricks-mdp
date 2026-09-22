# Private (pipeline-scoped, not published to UC) filtered view of
# bronze_acnc.charity_register_raw, feeding charity_register_scd1/scd2's
# snapshot source. Excludes the ~605 NULL-ABN rows (mostly Private
# Ancillary Funds -- see charity_register_quarantine.py) that have no
# stable identity for ABN-keyed SCD tracking. Unlike the removed
# `*_snapshot` wrapper views (phase3b-scd-snapshot-cleanup), this
# intermediate dataset does real filtering work, so it's justified rather
# than an unnecessary passthrough.
from pyspark import pipelines as dp


@dp.materialized_view(private=True)
@dp.expect_or_drop("has_abn", "ABN IS NOT NULL")
def charity_register_valid():
    return spark.read.table("bronze_acnc.charity_register_raw")
