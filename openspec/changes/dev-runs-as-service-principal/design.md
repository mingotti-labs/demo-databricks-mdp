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
- Implementation pilot (O8): with the human pipeline deleted and the SP granted
  `ALL PRIVILEGES, MANAGE`, the move run as the SP is refused: `User is not an
  owner of Pipeline '<deleted human pipeline>'`. The source's owner is still
  checked after deletion; the scratch test passed only because the human owned
  both. No move from a human pipeline to an SP pipeline is possible here.

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
- The 40 dev tables end up with the SP.

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

### D3. Drop and reload under the SP (revised after O8)
The first plan (delete the human pipeline, then a dev-only `move_dev_tables`
job run as the SP attaches the tables to the SP's pipeline) was built and
refused by O8; the job was removed. Per source, one at a time:
1. The user deletes the human pipelines; the tables stay.
2. Record counts (raw rows and files, SCD rows, closed SCD2 versions).
3. Drop the tables (explicit approval; the user runs the drops when the
   classifier blocks them).
4. The SP rebuilds them: `cicd/run_dev.py <unit> --param verify=true`, or for
   SEC its bronze and silver pipelines and two verify jobs by id, so its
   28-minute download is skipped (the replay already restores everything).
5. Compare counts for the replayable sources; read owners from Unity Catalog.

Order: yahoo bronze first (pilot, pipeline by id, no fetch), then portfolio,
wikipedia, sec, and yahoo's unit last (its Landing; `fetch_state` handed over
first with `ALTER TABLE ... OWNER TO <sp>`, which works for a plain table).

### D4. What a reload costs
SEC and Yahoo raw replay every landed file, and Bronze Publish is sequenced by
the fetch time stored in the files, so raw, SCD1 and SCD2 come back with the
same rows and versions (pilot: identical counts). Wikipedia and portfolio raw
are full loads, so their dev SCD2 history restarts from the reload. prd is
untouched.

### D5. Draft PRs for the dev check
CONTRIBUTING step 4: push the implementation branch, open the PR as a draft,
`deploy-dev` deploys as the SP, run the unit with `run_dev.py`, mark the PR
ready once verified. CLAUDE.md: the rule moves into Guardrails; "Operational
notes" says a deleted pipeline keeps its tables (probe, four times) and
replaces the list of human copies that own dev tables.

## Risks / Trade-offs

- Older sources' human-owned dev tables (neon, clickstream silver) need the
  same reload; neon's Lakeflow Connect ingestion re-reads Postgres.
- The hook is a text match on a command at the start of a line or after
  `;`, `&`, `|` or `(`: a command built indirectly could slip past. It targets
  the habit, not an adversary.
- The hook only loads for sessions whose project folder holds the settings
  file; the workspace folder gets a copy outside the repo.
- Free Edition runs one thing at a time: no dev runs while a prd deploy runs
  units.
