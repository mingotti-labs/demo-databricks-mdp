# Batch snapshot of bronze_ungm.unspsc_public_raw for snapshot-based Auto
# CDC. unspsc_public_raw is a Materialized View that re-fetches the
# complete UNSPSC tree on every run -- not append-only, same "full current
# state each pull" shape as Neon's upsert-maintained tables -- so streaming
# Auto CDC would fail the same way it did there (see
# phase3b-neon-scd-modeling's design.md). create_auto_cdc_from_snapshot_flow
# compares this batch snapshot against the one from its previous run
# instead of streaming change events.
from pyspark import pipelines as dp


@dp.materialized_view()
def unspsc_public_snapshot():
    return spark.read.table("bronze_ungm.unspsc_public_raw")
