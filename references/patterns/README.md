# Patterns bundle

Deployable reference implementations that are not part of any source's flow. Dev only; the
main bundle excludes `references/**`. Pipelines write to `pattern_bronze` and
`pattern_bronze_publish` (created by iac). Nothing here runs in CI except
`databricks bundle validate`.

Unlike the main bundle, you deploy this one yourself, from this folder:

```
cd references/patterns
databricks bundle validate -t dev --profile <PROFILE>
databricks bundle deploy   -t dev --profile <PROFILE>
```

Deploying creates pipelines and jobs, not tables. Tables, and so table slots, appear only
when you run a pipeline. The metastore holds 500 tables; a streaming table or materialized
view costs 2 slots (it has a hidden `__materialization_mat_*` twin). Check
`databricks resource-quotas get-quota metastore <metastore_id> table-quota` first.

## Lakeflow Connect, query-based, PostgreSQL (`bronze_lakeflow_query_postgresql`)

Managed ingestion pipeline reading Neon through the UC connection `neon_dev`, polling each
table by its `updated_at` column. No gateway, so no classic compute. Hard deletes at the
source are not propagated; a new table needs a new `table:` block.
Needs the live Neon project, the connection `neon_dev` and secret scope `neon-postgres` (iac).
Slots: about 9 while the tables exist (4 tables with twins, plus the pipeline's own).

```
databricks bundle run pattern_seed_neon                       --profile <PROFILE>   # reseeds Neon
databricks bundle run pattern_bronze_lakeflow_query_postgresql --profile <PROFILE>   # tables pattern_bronze.lakeflow_query_postgresql_*
databricks bundle run pattern_verify_lakeflow_query_postgresql --profile <PROFILE>   # row counts equal Neon's
```

Remove: `databricks bundle destroy -t dev --profile <PROFILE>` deletes the pipeline, and
Lakeflow Connect drops its tables with it, but not their hidden `__materialization_mat_*`
twins. Run `references/poc/table-cleanup/find_orphans.py --profile <PROFILE>` and drop the
`ORPHAN` twins it lists (`drop_tables.py` in the same folder).

## Auto Loader, `addNewColumns` (`bronze_autoloader_add_new_columns_python`)

Streaming table over JSON files in the volume `bronze_clickstream.s3_clickstream_raw` (iac),
with the schema evolution write-up in the file. The same volume feeds the other seven
Auto Loader variants in `src/bronze/`. Slots: 2.

```
databricks bundle run pattern_seed_clickstream_events           --profile <PROFILE>   # appends a batch of files; run it again later for a batch with a new column
databricks bundle run pattern_bronze_autoloader_add_new_columns_python --profile <PROFILE>
databricks bundle run pattern_verify_autoloader                 --profile <PROFILE>
```

A new column in a later batch stops the running update once, and Databricks starts a new one
by itself; the first `bundle run` that sees it reports a failure even though the pipeline recovers.

Remove: `databricks bundle destroy -t dev --profile <PROFILE>`, then drop what it leaves
(a regular pipeline's tables stay, with their twins):

```
DROP TABLE mdp_dev.pattern_bronze.autoloader_add_new_columns_python;
```

and the hidden `__materialization_mat_*` twin that `find_orphans.py` lists for it.

## Patterns that read another pattern

Run the source pattern first.

| Pattern | Reads |
|---|---|
| `bronze_publish_scd1_autocdc_stream_sql` | `pattern_bronze.autoloader_add_new_columns_python` |
| `bronze_publish_scd1_materialized_view_sql` | `pattern_bronze.lakeflow_query_postgresql_customers` |
| `bronze_publish_scd2_merge_sql` (job) | `pattern_bronze.lakeflow_query_postgresql_customers` |

After running any patterns, `databricks bundle run tag_patterns` sets each table's
`design_pattern` tag (register: `references/docs/registers/design-patterns.md`).
