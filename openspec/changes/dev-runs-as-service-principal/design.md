## Context

See proposal.md, Why. The probe (`references/poc/pipeline-ownership/README.md`,
2026-10-29, scratch pipelines in dev) established:

- `ALTER STREAMING TABLE|MATERIALIZED VIEW <t> SET
  TBLPROPERTIES('pipelines.pipelineId'=...)` needs one identity owning and
  running both pipelines (docs; refused as the human: `DESTINATION_PIPELINE_
  PERMISSION_DENIED`). A pipeline's owner cannot change on Free Edition (`Only
  metastore admins can change pipeline owner`; the metastore owner is `System
  user`), and the human cannot run jobs as the SP (no `servicePrincipal.user`).
- Deleting a pipeline keeps its tables (still pointing at the deleted id). A new
  pipeline does not adopt them, but the `ALTER` to it works once the source is
  gone, checking only the destination's owner. After the move the destination
  kept rows and SCD1 state, and its Auto Loader flow read only the new file.
- A pipeline table's owner follows its pipeline's run-as; `OWNER TO` is refused.

Dev inventory (2026-10-29), human pipeline → SP pipeline:

| Human pipeline | id | SP pipeline id | Tables |
|---|---|---|---|
| bronze--portfolio | `28c4e371` | `b6e3a5f8` | 6 raw MVs, 6 SCD2 |
| silver--portfolio | `6eab496a` | `b80f020d` | 6 |
| bronze--wikipedia | `e9968e01` | `bf6e1675` | raw MV, SCD2 |
| silver--wikipedia | `634ddab5` | `4757e5a9` | 1 |
| bronze--sec | `37d357dd` | `0fc4550f` | 2 raw, 2 SCD2 |
| silver--sec | `7810f676` | `cdb8656d` | 2 |
| bronze--yahoo | `00bac0f4` | `21a97027` | 4 raw, 3 SCD1, 1 SCD2 |
| silver--yahoo | `149d7048` | `00593c6f` | 4 |

Plus `bronze_yahoo.fetch_state` (plain table) and the human jobs
`run--{portfolio,wikipedia,sec,yahoo}--dev`. 40 tables in all.

## Goals / Non-Goals

**Goals:**
- The agent cannot deploy or run the main bundle under the human identity.
- Running a unit as the SP in dev is one command.
- The 40 dev tables end up with the SP, without a reload where the move works.

**Non-Goals:**
- Older sources' human-owned dev tables (neon, clickstream silver): same
  procedure later, per source.
- Granting the human `servicePrincipal.user` or changing iac.
- Stopping a human from deploying by hand: the hook guards the agent.

## Decisions

### D1. A Claude Code hook, not only a written rule
A `PreToolUse` hook on `Bash` and `PowerShell` runs `cicd/block_bundle_deploy.py`,
which reads the tool call from stdin and exits 2 (refuse, message to the agent)
when the command contains `databricks bundle deploy|run|destroy` and neither the
command nor the working directory names `references/patterns`. Any target is
refused: dev is the default target and tst/prd are CI-only already. `validate`,
`plan`, `summary` and all non-bundle commands pass. The check is a pure function
with unit tests. Alternative rejected: a stronger CLAUDE.md note (already there,
failed twice).

### D2. `cicd/run_dev.py`
Finds the job named `[dev svc_cicd_github] run--<unit>--dev` (the SP's
development-mode prefix), runs it with `jobs run-now --json` (job parameters as
JSON; `bundle run --params` parses values as CSV), polls until it ends, prints
the result and run page, exits 1 unless `SUCCESS`. `--profile` is required.
Pure parts (job name, payload) are unit-tested.

### D3. Delete first, then move as the SP
Per human pipeline:
1. Record row counts and closed SCD2 versions of its tables.
2. The user deletes the human pipeline (the classifier blocks the agent from
   deleting pipelines); its tables stay.
3. The human grants the SP rights on those tables (D5); the user runs the grant
   if the classifier blocks it.
4. `move_dev_tables` (SP) moves them to the SP pipeline.
5. The SP pipeline runs; counts compared with step 1; owner read from Unity
   Catalog.

Upstream before downstream, so an SP pipeline never reads a human table:
yahoo bronze first (pilot, it reads only its volume), then portfolio, wikipedia
and sec bronze, then the four silver pipelines. `fetch_state`: `ALTER TABLE ...
OWNER TO <sp>` by the human (catalog owner). Then the human jobs are deleted by
the user and `run_dev.py` runs portfolio, wikipedia, sec, yahoo with
`verify=true`, one at a time.

### D4. `move_dev_tables` job
A dev-only notebook job in the `dev` target of both edition sources (it never
exists in prd), parameters `catalog`, `pipeline_id`, `tables` (comma list of
`schema.table`). For each table: read its type from Unity Catalog, run the
matching `ALTER`, read back `pipeline_id`; collect failures and fail at the end
naming each. A no-op for a table already on the destination, so it can be
rerun. Runs as the SP because CI deploys it; triggered by id
(`databricks jobs run-now`), like the acnc migration job.

### D5. Which rights the SP needs
Not known yet: the SP's `ALTER` on a table it does not own may need `MODIFY`,
`MANAGE` or `ALL PRIVILEGES`. The pilot grants `MANAGE` and `ALL PRIVILEGES` on
the 8 yahoo bronze tables, records the result, and the rest use what worked.
Whether the owner becomes the SP when the SP pipeline runs is recorded too; if
it stays the human, the grants stay and the design records it.

### D6. Fallback: drop and reload, per source
If the SP's move or its first update fails for a source, its tables are
dropped (explicit approval each time) and the SP's `run_<unit>` rebuilds them.
SEC and Yahoo raw replay from the volume files; the other sources re-fetch.
Dev SCD2 history of portfolio and wikipedia would restart; prd is untouched.

### D7. Draft PRs for the dev check
CONTRIBUTING step 4: push the implementation branch, open the PR as a draft,
`deploy-dev` deploys as the SP, run the unit with `run_dev.py`, mark the PR
ready once verified. CLAUDE.md: the rule moves into Guardrails; "Operational
notes" says a deleted pipeline keeps its tables (probe, four times) and
replaces the list of human copies that own dev tables.

## Risks / Trade-offs

- The SP's move may be refused even with grants (D5) → D6 per source.
- A pipeline that has never run may not accept a moved table (an older note in
  `acnc-two-pipelines` says the destination must have run; today's docs do not)
  → if refused, start the SP pipeline once (it fails harmlessly on `already
  managed by pipeline`), then move again.
- The hook is a text match: a command built indirectly could slip past. It
  targets the habit, not an adversary.
- Free Edition runs one thing at a time: no dev runs while a prd deploy runs
  units.
