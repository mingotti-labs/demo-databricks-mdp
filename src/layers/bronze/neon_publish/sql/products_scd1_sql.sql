-- SCD Type 1 modeling of Neon's products table -- see
-- customers_scd1_sql.sql for why this is a plain passthrough, no AUTO CDC.
CREATE OR REFRESH MATERIALIZED VIEW products_scd1_sql
AS SELECT * FROM bronze_neon.products_raw;
