# SCD Type 2 (full history, __START_AT/__END_AT) modeling of ISO 3166-2
# subdivision codes. `source` points at subdivision_codes_deduped, a
# private intermediate in this same pipeline, not the raw table directly
# -- see that file's header for why (a genuine duplicate-key violation,
# confirmed via a real run).
#
# Keyed by (subdivision_code, language_code, subdivision_name), NOT
# subdivision_code alone -- confirmed via the real data before this was
# written that subdivision_code is not unique: 6,260 rows but only 5,046
# distinct codes, because a subdivision can have more than one localized
# name (e.g. AF-BDS has separate Dari/"fa" and Pashto/"ps" names for the
# same Afghan province). Adding language_code alone still leaves 175
# collisions (different transliterations of the same name in the same
# language, e.g. BY-BR's "Bresckaja voblasc" vs "Brestskaya voblasts'" both
# tagged "be"). Same category of finding as NSW Spatial's
# addressstringoid-vs-propid key correction -- caught via real data, not
# assumed from the CSV's column names or the original design.
#
# SCD2-only for this table (and country_codes) -- SCD1 dropped from this
# change's scope; low-change-frequency reference data doesn't need a
# separate "latest value" table when SCD2's `WHERE __END_AT IS NULL` gives
# the same thing.
#
# Bronze full pattern (openspec rollout-bronze-full-pattern): see
# country_codes_scd2.py. The per-load ingested_timestamp is dropped in
# subdivision_codes_deduped, so the snapshot has no untracked column.
from pyspark import pipelines as dp

dp.create_streaming_table(
    name="bronze_iso_publish.subdivision_codes_scd2",
    table_properties={
        "pipelines.reset.allowed": "false",
        "delta.enableChangeDataFeed": "true",
    },
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_iso_publish.subdivision_codes_scd2",
    source="subdivision_codes_deduped",
    keys=["subdivision_code", "language_code", "subdivision_name"],
    stored_as_scd_type=2,
)
