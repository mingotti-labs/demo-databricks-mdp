# Batch snapshot of bronze_neon.customers_raw for snapshot-based Auto CDC.
# NOT a streaming read -- customers_raw is upsert-maintained by Lakeflow
# Connect (cursor_columns-based query ingestion merges changed rows in
# place), so it is not an append-only source. A plain streaming Auto CDC
# flow against it fails with DELTA_SOURCE_TABLE_IGNORE_CHANGES the moment a
# real UPDATE lands (confirmed via a real failure -- see this pipeline's
# OpenSpec design.md). create_auto_cdc_from_snapshot_flow compares this
# batch snapshot against the one from its previous run instead of streaming
# change events, which matches what this source actually is.
from pyspark import pipelines as dp


@dp.materialized_view()
def customers_snapshot():
    return spark.read.table("bronze_neon.customers_raw")
