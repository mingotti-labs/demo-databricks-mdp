-- Pattern bronze_publish_scd1_materialized_view_sql: SCD Type 1 of an upserted
-- _raw table. bronze_neon.customers_raw is merged in place by Lakeflow Connect
-- (cursor-column query ingestion), so it already is "latest value per key"; a
-- plain passthrough materialized view satisfies SCD1, with no AUTO CDC.
-- Reference only. Reads the dev Neon customers.
CREATE OR REFRESH MATERIALIZED VIEW bronze_publish_scd1_materialized_view_sql
AS SELECT * FROM bronze_neon.customers_raw;
