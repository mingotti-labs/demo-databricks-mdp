## Why

acnc is the second Silver Normalised source and the first with repeating
groups: an operating-countries list and three flag families (operating
states, purposes, beneficiaries). It gives the bridge code from `phase4d`
its first real run. acnc's Landing lacks `ingested_timestamp`, the layer's
precondition; by the user's decision the bronze retrofit is part of this
change rather than a change of its own.

Profiling the full dataset (instead of `dev`'s 500-row sample) showed that
a sample can hide real conflicts: Postcode → State had 0 violations on the
sample and 157 on the full data. The change also folds in four framework
corrections found while proposing it.

## What Changes

- **Retrofit**: `bronze_acnc.charity_register_raw` stamps
  `ingested_timestamp`; `charity_register_valid` stamps
  `transformed_timestamp`; `charity_register_scd2` excludes both from
  history tracking. Silver Landing passes them through unchanged.
- **acnc normalised spec** `src/layers/silver/normalised/specs/acnc.yml`:
  base `charity_register`; bridges `charity_register_operating_state`,
  `_operating_country`, `_purpose`, `_beneficiary`; ten extracted entities;
  no hierarchy; no ignored columns.
- **Bundle**: `silver_normalised_acnc` pipeline and `silver_acnc` job
  (landing → normalised → tag), reusing the generic pipeline.
- **`dev` loads the full acnc dataset** (`acnc_row_limit: ""`); already in
  this propose PR, so PR CI deployed it under the CI service principal for
  profiling.
- **Framework corrections** (design.md): schema v0.2 `unpivot.columns`;
  null is not a value when resolving an extracted entity's parent;
  `ingested_timestamp` verified on current rows only; dependency evidence
  from full data for row-limited sources.
- Docs: `docs/normalised-spec/README.md` and `schema.json` (v0.2, in this
  propose PR so the spec validates), the prompt template (step 0 and pass 2
  on full data), NAMING.md (acnc retrofitted),
  `docs/registers/data-sources.md`, `docs/decision-register.md`, CLAUDE.md
  (acnc dev loads the full dataset).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `silver-normalised`: parent resolution ignores nulls; verification
  checks `ingested_timestamp` on current rows; dependency evidence comes
  from full data; bridges may select a flag family by explicit column list.

## Cross-repo dependencies

Depends on a new `phase4e-silver-normalised-acnc-schema` change in
`demo-databricks-iac`: the `silver_normalised_acnc` schema in each catalog,
with the same grants as `silver_normalised_airroi`. Applied before this
change's implementation deploys.

## Model

Opus to propose (four framework corrections and the first repeating
groups); Sonnet to implement (applies an agreed design and spec).

## Impact

- New bundle resources: one pipeline, one job. Bronze acnc pipelines gain
  two columns (no new resources).
- `dev` acnc pulls ~66k rows instead of 500 (free CKAN API).
- Framework code changes affect airroi too; its verification is rerun.
- No breaking changes to existing tables beyond the added columns.
