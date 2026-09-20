-- SCD Type 1 modeling of Neon's order_items table -- see
-- customers_scd1_sql.sql for why this is a plain passthrough, no AUTO CDC.
CREATE OR REFRESH MATERIALIZED VIEW order_items_scd1_sql
AS SELECT * FROM bronze_neon.order_items_raw;
