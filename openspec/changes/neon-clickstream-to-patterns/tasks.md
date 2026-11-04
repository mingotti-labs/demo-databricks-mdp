## 0. Evidence (done in the proposal PR)

- [x] 0.1 Read-only quota scan in `references/poc/table-cleanup/` (`find_orphans.py`,
      `count_by_schema.py`, outputs): no orphans, 483/500

## 1. Patterns bundle

- [ ] 1.1 neon: pipeline `pattern_bronze_lakeflow_query_postgresql` (D2), seed job, verify job
      with `verify_seed_data.py` and `verify_bronze_neon_ingestion.py` moved to
      `references/patterns/verification/` and pointed at the pattern tables
- [ ] 1.2 clickstream: pipeline `pattern_bronze_autoloader_add_new_columns_python`
      (source file moved to `references/patterns/src/bronze/autoloader_add_new_columns_python.py`),
      generator job, verify job with the three clickstream notebooks moved and pointed at
      the pattern table
- [ ] 1.3 Repoint `bronze_publish_scd1_autocdc_stream_sql`, `bronze_publish_scd1_materialized_view_sql`,
      `bronze_publish_scd2_merge_sql` (D4)
- [ ] 1.4 `tag_patterns`: tag the new pattern tables
- [ ] 1.5 `references/patterns/README.md`: deploy, run order, look, destroy, drop; slot cost per pattern
- [ ] 1.6 P1: deploy the patterns bundle from the branch, seed and run neon, run clickstream
      generator and pipeline, both verify jobs pass (results in `references/poc/table-cleanup/`)
- [ ] 1.7 P2: destroy; confirm Lakeflow Connect tables are gone and the Auto Loader table
      remains; drop it and its twin with approval; record in design.md and the probes register

## 2. Main bundle

- [ ] 2.1 Remove neon pipeline and jobs from `cicd/databricks/free.yml` and `standard.yml`;
      `uv run python cicd/apply_edition.py`
- [ ] 2.2 Remove clickstream pipelines and jobs from `resources/`, and their source,
      seed and verification files
- [ ] 2.3 `src/common/design_patterns.yml`: remove `neon`, `clickstream`;
      `verification/silver_landing_checks/clickstream.yml` and any bronze checks; fix tests
- [ ] 2.4 CI: patterns bundle `bundle validate` in `pr.yml`, both edition sources (D8)

## 3. Remove the dev pipelines (before merge)

- [ ] 3.1 User deletes the SP-owned dev pipelines `bronze--neon--lakeflow--dev`,
      `bronze--clickstream--dev`, `silver--clickstream--dev`
- [ ] 3.2 With approval, drop the remaining clickstream tables, twins and event logs;
      `find_orphans.py` shows none for them

## 4. Docs

- [ ] 4.1 `design-patterns.md` (rename to `bronze_lakeflow_query_postgresql`, code paths,
      used-by), `data-sources.md`, CLAUDE.md "Sources" and repository tree, NAMING.md mentions

## 5. Verify

- [ ] 5.1 `uv run pytest`, `openspec validate --strict`, bundle validate (both editions and patterns)
- [ ] 5.2 Draft PR deploy-dev succeeds; quota API re-read after the drops (expect about 467)
