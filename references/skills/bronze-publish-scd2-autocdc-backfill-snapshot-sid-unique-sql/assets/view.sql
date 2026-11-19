-- Pattern bronze_publish_scd2_autocdc_backfill_snapshot_sid_unique_sql (view part): one key per
-- version. Up to the cut-over (the last legacy date) the stored legacy key; after it a key from the
-- row's values and the start of its version. Run once, after the first pipeline update.
CREATE OR REPLACE VIEW {{target_catalog}}.{{target_schema}}.{{target}}_unique AS
SELECT CASE WHEN __START_AT <= TIMESTAMP'{{cutover}}' THEN {{sid}}
            ELSE xxhash64({{row_hash}}, __START_AT) END AS {{sid}},
       {{columns}}, __START_AT, __END_AT
FROM {{target_catalog}}.{{target_schema}}.{{target}};
