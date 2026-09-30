## Why

`phase4c` built the design-time half of Silver Normalised: rules N1–N10,
the normalised spec format, the design-time agent and the profiling job.
Nothing executes a normalised spec yet. This change builds the run-time
half: the generic pipeline, the tag step, the verification with its drift
check, and the CI check on specs.

A framework verified only by unit tests would first meet real data in a
later source change. So this change also normalises its first real source,
**airroi**, through the same design-time flow every later source follows:
profiled with the standard job (both passes, `profile.json` in this
change), spec proposed by the agent, reviewed here. airroi is chosen over
acnc, the original pilot, because its Landing tables already carry
`ingested_timestamp` (acnc needs a bronze retrofit first) and it exercises
the hierarchy rule (N5) and SCD2 history (N6) on both of its tables.

airroi has no repeating groups, so bridge entities (N2) and dependency
tolerances are covered by unit tests only here; acnc (`phase4e`) is their
first real run.

## What Changes

- New generic pipeline source `src/layers/silver/normalised/pipeline.py`,
  instanced per source as its own pipeline resource; it reads the source's
  normalised spec (path passed via pipeline `configuration`) and defines
  one materialized view per base, bridge and extracted entity, plus
  `value_lineage` and any `{entity}_quarantine`.
- New `src/common/normalised_spec.py` (pure Python: load a spec, check
  cross-references the JSON Schema cannot express, `rdm_proposed_match_key`
  rule, drift comparison) with pytest tests in `tests/common/`, and
  `src/common/silver_normalised.py` (the Spark transforms per entity kind).
- New generic notebooks `src/layers/silver/normalised/tag.py` (applies the
  `mdp.*` Unity Catalog tags with `ALTER MATERIALIZED VIEW … SET TAGS`
  after each refresh) and `verification/verify_silver_normalised.py`
  (parity, element counts, value completeness, key uniqueness, FK
  integrity, lineage totals, tags, timestamps, drift), with
  `resources/jobs/verify_silver_normalised.job.yml`.
- New `.github/workflows/pr.yml` job validating every
  `src/layers/silver/normalised/specs/*.yml` against
  `docs/normalised-spec/schema.json` and running `pytest`; the workflow's
  path filter gains `docs/normalised-spec/**` and `tests/**`.
- airroi, the first source: `src/layers/silver/normalised/specs/airroi.yml`
  (proposed here, from this change's `profile.json`),
  `resources/pipelines/silver_normalised_airroi.pipeline.yml`
  (`silver--normalised--airroi--${bundle.target}`) and the orchestrating
  `resources/jobs/silver_airroi.job.yml` (`silver--airroi--${bundle.target}`:
  landing → normalised → tag).
- `pyyaml` added as a project dependency and to the pipeline's
  `environment`, per the "declare dependencies in bundle config" guardrail.
- Docs: `silver.md` (Orchestration section now describes the real job; N3
  clarified for key columns; platform columns), `docs/normalised-spec/README.md`
  (platform columns, parent resolution, generated columns of extracted
  entities), `docs/registers/data-sources.md` (airroi "Consumed by Silver
  Normalised"), `docs/decision-register.md`.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `silver-normalised`: adds the run-time requirements (generic pipeline,
  platform columns, extracted-entity columns and parent resolution, tag
  step, orchestration, verification, CI validation) and clarifies that N3
  never splits a Landing natural key.

## Cross-repo dependencies

Depends on a new `phase4d-silver-normalised-airroi-schema` change in
`demo-databricks-iac`: the `silver_normalised_airroi` schema in each
catalog, with the same grants as `silver_landing_airroi`. This change's
airroi pipeline writes into that schema, so the iac change is applied
before this one's implementation is deployed. If the tag step needs an
explicit `APPLY TAG` grant beyond table ownership (verified during
implementation), it is added to that same iac change.

## Model

Opus — sets the run-time convention every later source reuses (generic
pipeline, tag step, verification), with no prior template in this repo.
Later source changes that only add a spec and bundle resources go to
Sonnet.

## Impact

- New bundle resources: one pipeline and two jobs (`silver_airroi`,
  `verify_silver_normalised`). The pipeline writes only to
  `silver_normalised_airroi`; the jobs write nothing but tags.
- Deploys to `dev` in the implementation PR, to `tst`/`prd` via CI/CD on
  merge. airroi pulls the same four markets in every target, so the dev
  run is representative of `prd`'s shape.
- `pr.yml` gains a job with no Databricks credentials; it adds a few
  seconds to PRs touching the bundle, specs, schema or tests.
- No change to existing pipelines, jobs or tables.
