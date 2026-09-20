-- SCD Type 1 modeling of Neon's orders table -- see
-- customers_scd1_sql.sql for why this is a plain passthrough, no AUTO CDC.
CREATE OR REFRESH MATERIALIZED VIEW orders_scd1_sql
AS SELECT * FROM bronze_neon.orders_raw;
