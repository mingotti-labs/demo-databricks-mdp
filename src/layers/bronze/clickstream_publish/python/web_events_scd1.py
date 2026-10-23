# SCD Type 1 modeling of clickstream events into bronze_clickstream_publish
# -- exists for downstream-usage consistency (publish is where governed/
# secured access will live later), not because events change: web_events_raw
# is genuinely append-only (Auto Loader only ever inserts, never merges), so
# unlike Neon's SCD pipelines, plain streaming Auto CDC works directly here
# -- no snapshot workaround needed (see phase3b-neon-scd-modeling's design.md
# for why Neon's upsert-maintained source needed one). Since each event_id
# only ever appears once, this is a mechanical passthrough in practice: SCD1
# never has anything to overwrite.
from pyspark import pipelines as dp

# Built by the single bronze pipeline (default schema bronze_clickstream), so the
# target is qualified. Change data feed feeds Silver Landing (openspec
# refactor-airroi-clickstream-neon).
dp.create_streaming_table(
    name="bronze_clickstream_publish.web_events_scd1",
    table_properties={"delta.enableChangeDataFeed": "true"},
)
dp.create_auto_cdc_flow(
    target="bronze_clickstream_publish.web_events_scd1",
    source="bronze_clickstream.web_events_raw",
    keys=["event_id"],
    sequence_by="timestamp",
    stored_as_scd_type=1,
)
