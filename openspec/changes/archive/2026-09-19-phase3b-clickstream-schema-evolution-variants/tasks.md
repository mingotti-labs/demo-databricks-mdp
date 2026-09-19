## 1. Reorganize the canonical pipeline

- [x] 1.1 Moved `src/layers/bronze/clickstream/web_events_raw.py` to
      `src/layers/bronze/clickstream/python_add_new_columns/web_events_raw.py`
      (`git mv`, preserving history)
- [x] 1.2 Updated `resources/pipelines/clickstream_autoloader.pipeline.yml`'s
      `libraries` glob and `name:` (display name only — resource key
      `clickstream_autoloader` unchanged)
- [x] 1.3 Enriched the file's header with the confirmed-live behavior
      write-up (schema-change auto-restart, non-zero CLI exit despite
      self-recovery) — previously in the OpenSpec design.md only, now also
      in the source itself for the interview-prep use case

## 2. Python variants

- [x] 2.1 Created `python_rescue/web_events_rescue.py` — documented from
      Databricks' docs, explicitly labeled as not independently re-verified
- [x] 2.2 Created `python_fail_on_new_columns/web_events_fail_on_new_columns.py`
      — same labeling
- [x] 2.3 Created `python_none/web_events_none.py` — same labeling
- [x] 2.4 Created the three corresponding `.pipeline.yml` resources, each
      with an isolated `libraries` glob pointing only at its own folder

## 3. SQL variants

- [x] 3.1 Verified `${key}` is the correct SQL parameter-substitution syntax
      for pipeline `configuration` values before writing any SQL (Databricks
      docs, not guessed)
- [x] 3.2 Created all four SQL variants
      (`sql_add_new_columns`/`sql_rescue`/`sql_fail_on_new_columns`/`sql_none`),
      each `inferColumnTypes => false` to match the Python variants' default
      for a fair comparison
- [x] 3.3 Created the four corresponding `.pipeline.yml` resources, each
      with an isolated `libraries` glob

## 4. Validate and deploy

- [x] 4.1 `databricks bundle validate` passed for `dev`/`tst`/`prd`
- [x] 4.2 `databricks bundle deploy -t dev` — `clickstream_autoloader` showed
      "Updated" (not "Created"); all 7 new pipelines showed "Created";
      7 created, 2 changed (pipeline + a pre-existing unrelated job), 0
      deleted, 5 unchanged
- [x] 4.3 Confirmed the canonical pipeline's `pipeline_id` unchanged
      (`82660efe-...`) and its table still has all 400 rows — the
      reorganization did not touch existing data
- [x] 4.4 Did not trigger any of the 7 new pipelines — per direct
      instruction, only `addNewColumns` needed re-proving, already done in
      `phase3b-clickstream-autoloader`
