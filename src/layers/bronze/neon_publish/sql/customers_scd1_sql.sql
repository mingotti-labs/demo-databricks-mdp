-- SCD Type 1 modeling of Neon's customers table, SQL sibling of
-- python/customers_scd1.py.
--
-- No AUTO CDC needed here at all: bronze_neon.customers_raw is
-- upsert-maintained by Lakeflow Connect (cursor_columns-based query
-- ingestion merges each changed row in place), which means it already IS
-- "latest value per key" -- the literal definition of SCD1. A plain
-- passthrough materialized view already satisfies it.
CREATE OR REFRESH MATERIALIZED VIEW customers_scd1_sql
AS SELECT * FROM bronze_neon.customers_raw;
