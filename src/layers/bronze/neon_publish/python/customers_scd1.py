# SCD Type 1 (latest-value-wins) modeling of Neon's customers table, via
# snapshot-based Auto CDC against customers_snapshot.py's batch read. See
# that file's header for why streaming Auto CDC doesn't work against this
# source. Replaces the retired bronze_neon_history pattern -- see
# demo-databricks-iac's phase3b-bronze-schema-simplification design.md.
from pyspark import pipelines as dp

dp.create_streaming_table(name="customers_scd1")
dp.create_auto_cdc_from_snapshot_flow(
    target="customers_scd1",
    source="customers_snapshot",
    keys=["id"],
    stored_as_scd_type=1,
)
