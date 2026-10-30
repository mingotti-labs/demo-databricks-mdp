## 1. Probe

- [x] 1.1 P1: scratch pipeline in dev (`pattern_bronze`), run, change its
      default schema to `pattern_bronze_publish`, run again; scripts and
      results in `references/poc/single-silver-landing-schema/`, a row in
      `references/docs/registers/probes.md`, result in design.md (scratch
      pipeline `c1fe1449` and its table dropped in 3.5)
- [x] 1.2 If P1 fails, apply D3's fallback (keep the old default schema) and
      note the follow-up in proposal.md

## 2. Code

- [x] 2.1 Landing entity files (`src/layers/silver/landing/**`): every
      `create_streaming_table` / `create_auto_cdc_flow` target becomes
      `silver_landing.<source>__<entity>`
- [x] 2.2 Silver pipelines (`resources/pipelines/silver_*.pipeline.yml` and
      neon's in `cicd/databricks/free.yml`): `schema: silver_landing` (per
      P1); keys and names unchanged
- [x] 2.3 `landing:` job parameters in `resources/jobs/run_*.job.yml` and
      `cicd/databricks/free.yml`
- [x] 2.4 `src/common/design_patterns.yml` (`silver_landing` per source) and
      `src/common/tag_design_patterns.py` (prefix filter); tests in
      `tests/common/test_design_patterns.py`
- [x] 2.5 `src/common/normalised_spec.py` (prefix check) and its tests;
      Normalised specs `acnc.yml`, `airroi.yml` (`from:`);
      `src/layers/silver/normalised/profile.py`
- [x] 2.6 `verification/verify_silver_landing.py`,
      `verification/verify_silver_normalised.py`,
      `migrations/acnc_reset_scd2.py`
- [x] 2.7 `uv run python cicd/apply_edition.py`; `uv run python -m pytest`;
      `databricks bundle validate`; no `silver_landing_` left outside
      `standard.yml`, archives and history docs (grep)

## 3. Dev (as the service principal)

- [x] 3.1 Draft PR; `deploy-dev` succeeds
- [x] 3.2 Per source, one at a time: run the unit with `cicd/run_dev.py
      <unit> --param verify=true` (airroi: `pipelines start-update` on its
      silver pipeline only, no paid fetch; neon, clickstream: by hand);
      `verify_silver_landing` passes on the new tables
- [x] 3.3 acnc and airroi: Silver Normalised verifies, and the run after the
      rebuild restamps 0 Normalised rows (D7)
- [x] 3.4 Design-pattern tags: each new table carries its pattern, no source
      tagged another's tables
- [x] 3.5 User approves; drop the 25 old dev Landing tables and their
      `__materialization_mat_*` twins; table quota back near 388
- [x] 3.6 With approval: drop probe P1's scratch pipeline `c1fe1449`,
      `pattern_bronze.zz_p1_default_schema` (and twin) and
      `pattern_bronze_publish.event_log_c1fe1449_...`

## 4. Docs

- [x] 4.1 NAMING.md (schema table, Landing table names),
      `references/docs/medallion/silver.md`, `references/docs/registers/`
      (design-patterns, data-sources, source_systems), normalised-spec README
      and schema.json, `silver-normalised-propose` skill and template
- [x] 4.2 CLAUDE.md: Landing names in "Sources"; "Operational notes" gets the
      table quota (500 per metastore, 2 slots per streaming table or
      materialized view, orphaned twins after drops) and the schema quota (50
      per catalog, count lags after a drop)

## 5. User clean-up

- [x] 5.1 User deletes the empty human dev geonames pipelines `d5259087`
      (bronze) and `50dcfbf4` (silver); drop any orphaned twins they leave
- [x] 5.2 User deletes the seven human dev silver pipelines still pointing at
      the old schemas (found 2026-10-30): `01125ee3` acnc, `058c25a6` ungm,
      `182fad45` airroi, `56313b36` iso, `92ede464` nsw_spatial, `c367686f`
      clickstream, `e20c0f21` neon; needed before iac drops the old schemas

## 6. prd

- [x] 6.1 Mark the PR ready; user merges; CI runs the units in prd
- [x] 6.2 Check the 22 new prd tables: row counts equal the old tables
- [x] 6.3 User approves; drop the 22 old prd Landing tables and their twins
- [x] 6.4 Confirm the twelve `silver_landing_<source>` schemas are empty in
      both catalogs; hand over to the iac follow-up
