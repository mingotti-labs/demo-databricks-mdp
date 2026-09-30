# Prompt: propose a source for Silver Normalised

The single copy of the design-time agent's instructions. Loaded by the
`silver-normalised-propose` skill; do not copy these instructions anywhere
else. Run on Opus.

**Input**: one `{source}` whose Silver Landing tables exist in `dev`.

## Fixed inputs

Read these first, in full. They are the rules every source is judged
against; do not restate them in your output, cite them.

- `docs/medallion/silver.md`, section "Silver Normalised" — rules N1–N10
- `NAMING.md` — "Silver Normalised tables" and "Platform-added timestamp
  columns"
- `docs/registers/data-sources.md` — the source's entry
- `docs/normalised-spec/schema.json` and `docs/normalised-spec/README.md`
- `CONTRIBUTING.md` — the two-PR flow and model selection

## Steps

### 0. Check the precondition

Every `silver_landing_{source}` table must have an `ingested_timestamp`
column. If any lacks it, stop: the source needs its bronze retrofit change
first (README, "Adding a source", step 0).

### 1. Profile, pass 1

Run the standard profiling job for the source on `dev`, alone on the
shared serverless pool (no other run in flight). Use `jobs run-now --json`
for both passes: `bundle run --params` parses its value as CSV, so pass 2's
JSON `dependency_pairs` breaks it.

```bash
JOB=$(databricks bundle summary -t dev --profile <PROFILE> --output json \
  | python -c "import json,sys; print(json.load(sys.stdin)['resources']['jobs']['profile_silver_normalised']['id'])")
databricks jobs run-now --profile <PROFILE> --output json \
  --json "{\"job_id\": $JOB, \"job_parameters\": {\"source\": \"{source}\"}}"
databricks jobs get-run-output <task_run_id> --profile <PROFILE> --output json
```

`run-now` waits for the run to finish; `<task_run_id>` is `tasks[0].run_id`
in its output. Check `notebook_output.truncated` is `false` before using
the result; if it is `true`, stop and report — the profile is incomplete.
The run output's `notebook_output.result` is a JSON document:

- `tables[]`: `table`, `row_count`, `columns[]` with `column`, `type`,
  `null_pct`, and for non-complex types `distinct_count`, `max_length`,
  `delimiter_rows` (rows containing `;`, `,`, `|`) and `top_values[]`
  (`value`, `rows`; top 20)
- `value_overlaps[]`: `table_a`, `column_a`, `table_b`, `column_b`,
  `shared_values` — distinct values shared by two string columns, for
  columns with at most `overlap_max_distinct` distinct values

Profiles cover all SCD2 versions, not only current rows.

### 2. Find repeating groups and domains

- **Repeating groups (N2)**: columns with high `delimiter_rows` whose
  `top_values` look like lists; families of flag columns (`distinct_count`
  of 1 or 2 with values like `Y`/`N`, `true`/`false`). Do not rely on a
  shared name prefix: acnc's beneficiary flags (`Adults`, `Children`,
  `Youth`…) have none. A flag family shows in `value_overlaps` as many
  column pairs sharing the same single value; group them by meaning.
- **Domains (N7)**: coded attributes — low `distinct_count` relative to
  `row_count`, short `max_length`, code-like `top_values`, names such as
  `country`, `ctry`, `state`, `status`, `category`, `currency`. Group
  columns into one domain by meaning, confirmed by `value_overlaps`, never
  by name alone. Every coded column belongs to a domain, even if it is the
  only member (N7).

### 3. Profile, pass 2: dependencies

List candidate dependencies (N3, N4, N5): attributes that look determined
by a non-key attribute or by part of a composite key, and chains such as
locality → region → country. Rerun the job with them:

```bash
databricks jobs run-now --profile <PROFILE> --output json --json '{
  "job_id": <JOB>,
  "job_parameters": {
    "source": "{source}",
    "dependency_pairs": "[{\"table\":\"t\",\"determinant\":\"a\",\"dependent\":\"b\"}]"
  }
}'
```

`dependency_pairs` is a JSON list passed as a string parameter.

Output: `dependency_checks[]`, each pair plus `violating_values`. A split
is only proposed at `violating_values = 0` (N4). A non-zero result stays
denormalised unless you propose a `dependency_tolerance`, with the reason.

Save both outputs, merged, as `profile.json` in the openspec change folder.

### 4. Propose

On a `feature/silver-normalised-{source}` branch, create the openspec
change `phase4x-silver-normalised-{source}` per CONTRIBUTING.md and write:

- `src/layers/silver/normalised/specs/{source}.yml` — valid against
  `schema.json`; every Landing column either used or in `ignored_columns`
- `design.md` from `docs/templates/silver-normalised-design.md`, citing
  `profile.json` numbers for every entity, domain, split and tolerance
- `proposal.md` (`## Model`: Opus to propose, Sonnet to implement;
  `## Cross-repo dependencies`: the `silver_normalised_{source}` schema and
  grants in `demo-databricks-iac`) and `tasks.md`

Validate before finishing:

```bash
uvx check-jsonschema --schemafile docs/normalised-spec/schema.json src/layers/silver/normalised/specs/{source}.yml
openspec validate phase4x-silver-normalised-{source} --strict
```

### 5. Stop for review

Commit as `propose:`, open the propose PR, and stop. Nothing is deployed
from an unreviewed spec. Report the entities, domains and any tolerance
the reviewer should look at first.

## Never

- Correct, map or clean a value (that is rdm's job)
- Read from another source's schema or from rdm
- Propose a split whose dependency has exceptions without a declared
  tolerance and reason
- Put an LLM call in anything that runs at pipeline run time
