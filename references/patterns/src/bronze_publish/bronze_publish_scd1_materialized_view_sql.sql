-- Pattern bronze_publish_scd1_materialized_view_sql: SCD Type 1 of an upserted
-- _raw table. pattern_bronze.lakeflow_query_postgresql_customers is merged in place by Lakeflow Connect
-- (cursor-column query ingestion), so it already is "latest value per key"; a
-- plain passthrough materialized view satisfies SCD1, with no AUTO CDC.
-- Reference only. Reads pattern_bronze.lakeflow_query_postgresql_customers: run that pattern first.
CREATE OR REFRESH MATERIALIZED VIEW bronze_publish_scd1_materialized_view_sql
AS SELECT * FROM pattern_bronze.lakeflow_query_postgresql_customers;
