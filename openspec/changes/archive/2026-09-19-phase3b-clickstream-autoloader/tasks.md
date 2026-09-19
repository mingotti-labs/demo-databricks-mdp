## 1. Seed data generator

- [x] 1.1 Create `src/seed_data/generate_clickstream_events.py` — `Faker`-based,
      generates a batch of clickstream event JSON files, writing to the
      landing path; each run writes a new, distinctly-named batch — verified
      by running it twice: `batch_000.json` then `batch_001.json`, both present
- [x] 1.2 Added a later-batch code path (`batch_number > 0`) that includes
      `device_type` and `referrer_url`, absent from the first batch — verified
      by inspecting `DESCRIBE TABLE` after ingesting both batches

## 2. Job wrapping the generator

- [x] 2.1 Created `resources/jobs/generate_clickstream_events.job.yml` — 
      `databricks bundle validate` passed for `dev`/`tst`/`prd`

## 3. Auto Loader pipeline

- [x] 3.1 Created `src/layers/bronze/clickstream/web_events_raw.py` — Streaming
      Table via `cloudFiles`, `schemaEvolutionMode = addNewColumns` set
      explicitly, `schemaLocation` not set
- [x] 3.2 Created `resources/pipelines/clickstream_autoloader.pipeline.yml` —
      used `schema:` (not the legacy `target:`) per `databricks bundle
      schema`'s own field description; catalog value passed into the pipeline
      source via a `configuration` block + `spark.conf.get()`, since
      `cloudFiles.load()`'s path isn't auto-parameterized the way dataset
      names are — validated for `dev`/`tst`/`prd`

## 4. Deploy and run (dev)

- [x] 4.1 `databricks bundle deploy -t dev` — no errors
- [x] 4.2 `databricks bundle run generate_clickstream_events -t dev` — batch 0
      (200 events) landed at
      `/Volumes/mdp_dev/bronze_clickstream/s3_clickstream_raw/web_events/landing/batch_000.json`
- [x] 4.3 `databricks bundle run clickstream_autoloader -t dev` — 
      `mdp_dev.bronze_clickstream.web_events_raw` created with 200 rows,
      matching the file record count exactly
- [x] 4.4 No permission error surfaced for the CI/CD-vs-human distinction
      flagged in `phase3b-clickstream-volume`'s design.md (this run used the
      deploying human identity, `handsonessential@gmail.com`, which already
      had access) — genuinely different issue surfaced instead, at the target
      level, not the volume level: see task 7.1's note on `tst` deploy
      ownership

## 5. Schema evolution proof

- [x] 5.1 Ran the seed job again — `batch_001.json` written with
      `device_type`/`referrer_url` included
- [x] 5.2 Re-ran the pipeline. First attempt failed outright with
      `RESOURCE_EXHAUSTED` (Free Edition's shared serverless compute pool —
      unrelated to schema evolution; resolved by stopping an idle
      `RUNNING` SQL warehouse eating the quota, see CLAUDE.md's new
      "Operational notes"). Second attempt: the flow terminated once with
      `"... encountered a schema change during execution and terminated"`, the
      update was `CANCELED` (cause `SCHEMA_CHANGE`), and Databricks
      automatically started and completed a new update (cause
      `SCHEMA_CHANGE`) — confirmed via `databricks pipelines list-updates`.
      `web_events_raw` ended with 400 rows total, 200 with `device_type`
      populated (the other 200, from batch 0, are `NULL`) — exactly the
      expected schema-evolution behavior, and the design.md's previously
      "unverified" risk is now confirmed and documented with the real event
      log text

## 6. Verification suite

- [x] 6.1 Created `verification/verify_clickstream_files.py`
- [x] 6.2 Created `verification/verify_clickstream_ingestion.py`
- [x] 6.3 Created `verification/verify_clickstream_schema_evolution.py`
- [x] 6.4 Created `resources/jobs/verify_clickstream_pattern.job.yml` — full
      run against `dev` passed end-to-end: `verify_files` (2 files, 400
      records), `verify_ingestion` (400 rows), `verify_schema_evolution` (400
      total, 200 with `device_type`)

## 7. Promote and document

- [x] 7.1 Deployed to `prd` cleanly (12 created, 1 changed, 1 unchanged — a
      genuinely first-ever deploy to that target, no pre-existing owner
      conflict). **`tst` deploy failed**: `403 PERMISSION_DENIED: Only
      metastore admins can change pipeline owner` on the pre-existing
      `neon_ecommerce_ingestion` pipeline, which is owned by the CI/CD service
      principal from an earlier GitHub-Actions-driven deploy — a local human
      identity can't reassign that ownership. Documented in CLAUDE.md's new
      "Operational notes": `tst`/`prd` should be deployed via CI/CD (merge to
      `main`), not a local human `bundle deploy`, once a target has any
      SP-owned resources in it. Did not force this locally (would mean
      touching another resource's ownership without a clear reason to).
      `tst`'s actual promotion is expected to happen through this PR's merge
      and the existing `main.yml` GitHub Actions deploy, matching how
      `neon_ecommerce_ingestion` itself got there originally
- [x] 7.2 Updated CLAUDE.md's "Sources" section with a clickstream entry
- [x] 7.3 Added `src/layers/bronze/clickstream/` to CLAUDE.md's
      repository-structure tree, and refined the `src/seed_data/` description
      to cover both the truncate-and-reseed and append-a-batch shapes
- [x] 7.4 Documented real gotchas found during implementation directly in
      CLAUDE.md: the schema-evolution auto-restart behavior and its non-zero
      CLI exit code (in "Sources"), and the CI/CD-vs-human deploy-ownership
      trap plus the serverless-compute-quota trap (in new "Operational
      notes") — no separate manual-walkthrough doc was needed, since none of
      these are UI-specific like 3a's gotchas were
