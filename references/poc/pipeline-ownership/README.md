# Pipeline ownership probe

Question: can tables built by a human-owned dev pipeline (`[dev handsonessential]
...`) be handed to the CI/CD service principal's copy of that pipeline without a
reload, with `ALTER STREAMING TABLE|MATERIALIZED VIEW <t> SET
TBLPROPERTIES('pipelines.pipelineId'='<sp pipeline>')` plus `OWNER TO <sp>`? And
does a moved Auto Loader table keep its checkpoint (no file read twice)?

Known before (acnc-two-pipelines, probes P1-P5): the move keeps rows and SCD2
history when one identity owns and runs both pipelines. Not covered: a human
source pipeline, an SP destination, an Auto Loader table, a plain table.

## Setup (dev, 2026-10-29)

- `zz_probe_pipeline.py`: `bronze_yahoo.zz_probe_raw` (Auto Loader over
  `/Volumes/mdp_dev/bronze_yahoo/s3_raw/zz_probe/landing`), `zz_probe_scd1`
  (SCD1 Auto CDC), `zz_probe_mv` (materialized view). Uploaded to
  `/Workspace/Shared/poc/pipeline-ownership/`.
- `landing/`: `f1.jsonl`, `f2.jsonl` landed first; `f3.jsonl` lands after the move.
- H: `pipeline_human.json`, created with the human profile
  (`0ed46408-2fba-487e-96d3-995c7ba59f8f`). First run: raw 4, scd1 3, mv 3, all
  owned by `handsonessential@gmail.com`, pipeline H.
- S: `pipeline_sp.json` / `create_sp_pipeline.py`, to be created by the SP through
  `submit_as_sp.json` (a one-time job with `run_as` the SP).

## Results

- Creating S as the SP: **blocked**. `jobs submit` with `run_as` the SP fails:
  `Cannot bind the service principal provided in 'run_as' field (svc-cicd-github)
  to the job. The user creating or updating the job must have
  'servicePrincipal.user' role on the service principal.` Being a workspace admin
  is not enough.
- Switched to the real dev Yahoo bronze (user, option 2): move the 8 tables of
  `[dev handsonessential] bronze--yahoo--dev` (`00bac0f4-...`) to the SP's copy
  `[dev svc_cicd_github] bronze--yahoo--dev` (`21a97027-...`, never run, same
  deployed code as the branch). Baseline (`baseline.sql`): prices_raw 133,105
  rows / 44 files, events_raw 52,148 / 15, calendar_raw 2,068 / 44, options_raw
  2,068 / 44, prices_scd1 129,753, events_scd1 52,048, options_scd1 517,
  calendar_scd2 517 (0 closed). All owned by the human, pipeline `00bac0f4`.
- `ALTER STREAMING TABLE mdp_dev.bronze_yahoo.prices_raw SET TBLPROPERTIES
  ('pipelines.pipelineId'='21a97027-...')` as the human (workspace admin, table
  and catalog owner): **refused**, nothing changed:
  `[DESTINATION_PIPELINE_PERMISSION_DENIED] ... you are not the owner of the
  destination pipeline ... Only owners can change the pipeline of a table.`
  So the move must be run by the SP (owner of the destination). The human owns
  `mdp_dev`, so `OWNER TO <sp>` on a table can be undone by the human.
- Databricks docs ("Move tables between pipelines",
  https://docs.databricks.com/aws/en/ldp/move-table, read 2026-10-29): the
  identity running the move must **own and be the run-as of both** pipelines;
  stop the source first; the source then treats the table as external; a table
  can be moved back the same way. Nothing on streaming checkpoints. So neither
  the human (owns the source) nor the SP (owns the destination) can move it
  as things stand.
- Making the SP the owner of human pipeline H (run by the user, since the
  agent's auto-mode classifier blocks permission changes):
  `permissions update pipelines <H>` with `IS_OWNER` for the SP: `The pipeline
  must have exactly one owner.` (update adds; the human stays owner).
  `permissions set pipelines <H>` (replaces): `Only metastore admins can change
  pipeline owner`. The metastore owner is `System user`, so on Free Edition no
  one can change a pipeline's owner.

- Delete first (user's idea), on scratch pipeline H:
  - `pipelines delete <H>`: the three tables **stay**, owned by the human, their
    `pipeline_id` still H's (deleted) id. (CLAUDE.md says a deleted pipeline
    drops its tables; not here, a fourth time.)
  - A new pipeline H2 (human, same code) does **not** adopt them: its update
    fails with `Table ... is already managed by pipeline <H>` (the deleted one).
  - `ALTER STREAMING TABLE|MATERIALIZED VIEW ... SET
    TBLPROPERTIES('pipelines.pipelineId'='<H2>')` as the human (owner and run-as
    of H2): **works** for all three; Unity Catalog shows H2.
  - H2 run with no new file: raw 4, scd1 3, mv 3 (unchanged: no file read
    again). After landing `f3.jsonl`: raw 5, scd1 3 with `b` = 3, mv 3. **The
    Auto Loader checkpoint moves with the table.**
  - `ALTER STREAMING TABLE ... OWNER TO <sp>` on a pipeline's table:
    `CHANGE_OWNER_NOT_ALLOWED_FOR_PIPELINE_TABLE ... Modify the run-as identity of
    the pipeline instead.` After deleting H2 too (table orphaned):
    `CHANGE_OWNER_FROM_INVALID_WORKSPACE` (same workspace; the check seems to
    fail on the missing pipeline). A pipeline table's owner follows its
    pipeline's run-as; it cannot be handed over directly.

## Conclusion (so far)

- Human pipeline to SP pipeline, as things stand: refused (one identity must own
  both, and a pipeline's owner cannot change on Free Edition).
- After the source pipeline is deleted, only the destination's owner is checked,
  and the move keeps rows, SCD1 state and the Auto Loader checkpoint.
- Still to prove, with a job run as the SP (deployed by CI): after the user
  deletes a human pipeline and the human grants the SP rights on its tables, can
  the SP move them to its own pipeline, and does the table owner become the SP
  when the SP's pipeline runs? Fallback: drop and reload (SEC and Yahoo raw
  replay from the volume files).

## Pilot: real dev Yahoo bronze

- The user deleted `[dev handsonessential] bronze--yahoo--dev` (`00bac0f4`):
  all 8 tables stay, owned by the human, `pipeline_id` still `00bac0f4` (the
  pipeline itself: `not found`).
- Counts before the move: unchanged from the baseline.
- `GRANT ALL PRIVILEGES, MANAGE ON TABLE ... TO <sp>` on the 8 tables, as the
  human: allowed.
- `move_dev_tables` run as the SP (run `130506019658393`, destination
  `21a97027`): **refused for all 8**, nothing changed:
  `PERMISSION_DENIED: User is not an owner of Pipeline '00bac0f4-...'` (the
  deleted human pipeline). The source pipeline's owner is still checked after
  it is deleted; on scratch H it passed only because the human owned both.

## Conclusion

**Fail.** A table built by a human-owned pipeline cannot reach an SP pipeline
without a reload on Free Edition: the move checks the owner of the source
pipeline (even deleted) and of the destination, a pipeline's owner cannot
change, and the human cannot act as the SP. Moves between pipelines of one
owner still work (acnc-two-pipelines P1-P5; O6 here, including the Auto Loader
checkpoint). Human-owned dev tables are dropped and rebuilt by the SP's
pipelines; append-only raw (SEC, Yahoo) replays every file from the volume, so
its SCD2 history is rebuilt too.

## Fallback on the pilot: drop and reload (user approved, 2026-10-29)

- Dropped the 8 human-owned tables; started the SP's pipeline `21a97027` by id
  (update `0e403522`, no fetch): COMPLETED.
- Counts identical to the baseline (prices_raw 133,105 / 44 files, events_raw
  52,148 / 15, calendar_raw and options_raw 2,068 / 44, prices_scd1 129,753,
  events_scd1 52,048, options_scd1 517, calendar_scd2 517 versions, 0 closed).
  Owner the SP, pipeline `21a97027`. Replaying the volume rebuilt raw, SCD1 and
  the SCD2 calendar exactly.
