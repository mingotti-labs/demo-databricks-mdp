# SCD Type 1 (latest-value-wins) modeling of Neon's customers table, via
# snapshot-based Auto CDC. `source` points directly at
# `bronze_neon.customers_raw` -- confirmed via a real run that
# create_auto_cdc_from_snapshot_flow does NOT require its source to be a
# dataset within this pipeline's own dataflow graph; an earlier version of
# this file wrapped the read in an intermediate snapshot materialized view
# (following the Databricks docs' example pattern literally) before this was
# tested and found unnecessary. Replaces the retired bronze_neon_history
# pattern -- see demo-databricks-iac's phase3b-bronze-schema-simplification
# design.md.
from pyspark import pipelines as dp

dp.create_streaming_table(name="customers_scd1")
dp.create_auto_cdc_from_snapshot_flow(
    target="customers_scd1",
    source="bronze_neon.customers_raw",
    keys=["id"],
    stored_as_scd_type=1,
)
