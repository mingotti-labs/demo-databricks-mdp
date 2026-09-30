## Context

See proposal.md for why. Builds on the archived
`phase4c-silver-normalised-design-time` (rules N1–N10, normalised spec
schema v0.1, the design-time agent, the profiling job) and its baseline
spec `openspec/specs/silver-normalised/spec.md`.

This document has two parts: **the framework** (run time, reused by every
source) and **airroi** (the first source, in the shape of
`docs/templates/silver-normalised-design.md`).

Current state:
- Silver Landing pipelines exist per source
  (`silver--landing--{source}--${bundle.target}`), each a set of Python
  materialized views, importing `src/common/` via the
  `sys.path.insert(workspace_file_path/src)` pattern.
- `silver.md` reserves `silver--normalised--{source}--${bundle.target}` and
  the orchestrating job `silver--{source}--${bundle.target}`.
- `@dp.materialized_view` has no tags parameter (its parameters are name,
  comment, spark_conf, table_properties, path, partition_cols,
  cluster_by_auto, cluster_by, schema, refresh_policy, row_filter,
  private). Applying tags to pipeline-created datasets with `ALTER
  MATERIALIZED VIEW … SET TAGS` has been GA since February 2026.
- Custom Spark code serialised to worker processes does not inherit the
  driver's `sys.path` fix (ACNC's `ModuleNotFoundError`, CLAUDE.md).

## Goals / Non-Goals

**Goals:**
- One generic pipeline source that executes any valid normalised spec.
- Tags, verification (incl. drift) and CI spec validation, all generic.
- Prove the framework end to end on a real source (airroi) in `dev`.

**Non-Goals:**
- Bridges and tolerances on real data (airroi has neither; acnc,
  `phase4e`, is their first real run). Covered by unit tests here.
- A `columns_like` alternative for flag families without a shared prefix
  (acnc's schema minor bump, `phase4e`).
- A surrogate-key pass-through attribute: no Landing table carries one
  today (N1's pass-through clause stays unexercised until one does).
- Governed tags, first/last-seen columns (planning backlog).
- Retrofitting `ingested_timestamp` to any source.

# Part 1: the framework

## Code layout

| File | Role | Tested by |
| --- | --- | --- |
| `src/common/normalised_spec.py` | Pure Python: `load_spec(path)` (YAML + cross-reference checks), `match_key(value)`, `drift(spec, landing_columns)`, platform-column constants | pytest, `tests/common/test_normalised_spec.py` |
| `src/layers/silver/normalised/transforms.py` | Spark transforms: `base`, `bridge`, `extracted`, `value_lineage`, `quarantine` DataFrames from a spec | airroi run (base, extracted, lineage); bridge/quarantine first real run in acnc |
| `src/layers/silver/normalised/pipeline.py` | Thin: reads `workspace_file_path` + `normalised_spec` from the pipeline configuration, loads the spec, registers one `@dp.materialized_view` per table in a loop | airroi run |
| `src/layers/silver/normalised/tag.py` | Notebook: `ALTER MATERIALIZED VIEW … SET TAGS` per table | airroi run |
| `verification/verify_silver_normalised.py` | Notebook: every check below, for one `source` | airroi run |

The pipeline's `libraries` names `pipeline.py` as a single `file`, not a
glob over `src/layers/silver/normalised/`: that folder also holds the
`profile.py` and `tag.py` notebooks, which call `dbutils.widgets` and must
not be loaded as pipeline sources.

A pipeline resource per source differs only in name, schema and spec path:

```yaml
resources:
  pipelines:
    silver_normalised_airroi:
      name: silver--normalised--airroi--${bundle.target}
      catalog: ${var.catalog}
      schema: silver_normalised_airroi
      serverless: true
      continuous: false
      configuration:
        workspace_file_path: ${workspace.file_path}
        normalised_spec: src/layers/silver/normalised/specs/airroi.yml
      environment:
        dependencies: [pyyaml]
      libraries:
        - file:
            path: ../../src/layers/silver/normalised/pipeline.py
```

`pyyaml` is declared in the bundle (guardrail: no `%pip install`) and
added to `pyproject.toml` for the tests. Whether serverless jobs (tag,
verify) already ship PyYAML is checked in implementation; if not, the
jobs declare it in an `environments` block.

## Spec loading and cross-reference checks

`load_spec` fails the pipeline at graph initialisation, before any table
is built, when a spec breaks a rule the JSON Schema cannot express. v0.1
checks:

- Every `from` is in `silver_landing_{source_system}`.
- Entity names are unique across the three blocks; none is
  `value_lineage` or ends in `_quarantine`.
- `bridge.parent` is a key of `base_entities`, and `bridge.from` equals
  the parent's `from` (a bridge flattens its parent's own rows).
- Every extracted target (a base entity's `extracted` value, a bridge's
  `extracted`) is a key of `extracted_entities`, and every extracted
  entity has at least one member column.
- `extracted_entities.{name}.parent` exists and the parent chain has no
  cycle.
- **Parent and attribute resolution**: for every base entity holding a
  member column of an extracted entity with a `parent`, exactly one column
  of that same base entity maps to the parent entity; every `attributes`
  column exists in that base entity. An extracted entity with a parent or
  attributes cannot have bridge members in v0.1 (a bridge row has no
  sibling columns to resolve them from).
- `dependency_tolerance.entity` is a base entity whose natural key or
  columns include both `determinant` and `dependent`.
- No column is both used and in `ignored_columns`.

Each rule is added because the pipeline would otherwise produce wrong or
ambiguous rows silently. The restrictions are v0.1 limits, relaxed by a
schema minor bump when a real source needs it.

## Platform columns

The pipeline carries the platform columns itself; a spec never lists them
and the drift check never counts them: `scd_valid_from_timestamp`,
`scd_valid_to_timestamp`, `is_current`, `source_name`, `source_file_name`,
`ingested_timestamp`, `transformed_timestamp`.

| Table | Platform columns |
| --- | --- |
| Base | Validity columns when `history: scd2`; `source_name`, `source_file_name`, `ingested_timestamp` passed through; `transformed_timestamp` restamped |
| Bridge | Parent's validity columns when the parent is `scd2` (N6: inherited); `ingested_timestamp` passed through; `transformed_timestamp` restamped |
| Extracted, `value_lineage` | `ingested_timestamp` = `max()` of aggregated rows; `transformed_timestamp` restamped |
| `{entity}_quarantine` | Same columns as its base entity |

If a Landing table has validity columns and its base entity omits
`history: scd2`, the pipeline fails: without them the natural key is not
unique across versions.

## Tables the pipeline builds

**Base entity** — Landing rows (minus quarantined ones, below), columns in
order: `natural_key`, `columns`, `extracted` keys not already in the key,
then platform columns. Natural-key columns get the comment "Natural key"
(Landing's convention). Unique on natural key (+
`scd_valid_from_timestamp` when `scd2`).

**Bridge entity** — parent natural key, parent validity columns, then one
element column named after the bridge's attribute (bridge name minus
`{parent}_`). `explode` splits the list column on the literal delimiter
and keeps non-null elements exactly as split: no trimming (N8's variants
are rdm's job). `unpivot` emits one row per column whose name matches
`columns_like` and whose value equals `keep_when`; the element is the
column name. Unique on parent key + validity + element.

**Extracted entity** — built from the same non-quarantined Landing rows
as its base entities (attribute columns exist only there) and from the
bridge entities, so quarantined rows are excluded consistently. One row per
distinct non-null member value across all members and all SCD2 versions
(N7), columns:

| Column | Source |
| --- | --- |
| `{entity}` | The value, unchanged; comment "Natural key" |
| `{parent}` | The parent's value from the same row (N5), when `parent` is set |
| attributes | From the same row (N7, N10), when set |
| `rdm_proposed_match_key` | `match_key(value)` (N8) |
| `row_count` | Occurrences across all members |
| `ingested_timestamp`, `transformed_timestamp` | See Platform columns |

Rows are grouped by value, parent and attributes, never picked by
`max()`/`first()`: if new data breaks a dependency, the value gets two
rows and verification's uniqueness check fails, instead of Silver silently
choosing a winner. That failure sends the source back to profiling, as
N4 intends.

**`value_lineage`** — `entity`, `value` (cast to string, since entities
differ in type), `source_table`, `source_column`, `row_count`, plus
timestamps. For an `unpivot` bridge, `source_column` is the flag column.

**`{entity}_quarantine`** — only for a base entity with a
`dependency_tolerance`. Violating determinant values are computed on the
Landing table (`GROUP BY determinant HAVING count(DISTINCT dependent) > 1`);
their rows go to the quarantine table, all other rows to the base entity
and its bridges.

### Match key

`match_key` is plain Python (NFKD normalise, drop combining marks, collapse
whitespace, trim, uppercase), unit-tested (`Vitória da Conquista` →
`VITORIA DA CONQUISTA`, `  AuStRaLiA ` → `AUSTRALIA`). It runs as a Python
UDF on extracted entities only (a few rows per domain). Because UDFs are
serialised to worker processes that lack the driver's `sys.path` fix, the
pipeline registers `common.normalised_spec` with
`cloudpickle.register_pickle_by_value`, so the function travels by value.
If that does not work on serverless, the fallback is an inline copy in
`pipeline.py`; the airroi run decides, since `Vitória da Conquista` is in
its data.

## Tags

`tag.py` (parameters `catalog`, `source`, `workspace_file_path`) loads the
spec and runs, per table:

```sql
ALTER MATERIALIZED VIEW {catalog}.silver_normalised_{source}.{table}
SET TAGS ('mdp_layer' = 'silver_normalised',
          'mdp_source_system' = '{source}',
          'mdp_entity_kind' = 'base' | 'bridge' | 'extracted')
```

`value_lineage` and quarantine tables get `mdp_layer` and
`mdp_source_system` only, since they are not an entity kind. The step is
idempotent and runs after every refresh, so it does not depend on whether
a refresh keeps tags (checked in implementation, recorded either way).
The table owner is the pipeline's run-as identity, which also runs the
job; whether ownership suffices or an `APPLY TAG` grant is needed is
checked in `dev` and, if needed, added to the iac change.

## Orchestration

`resources/jobs/silver_{source}.job.yml`, per source, as `silver.md`
reserves:

| Task | Type | Depends on |
| --- | --- | --- |
| `landing` | `pipeline_task` → `silver_landing_{source}` | — |
| `normalised` | `pipeline_task` → `silver_normalised_{source}` | `landing` |
| `tag` | `notebook_task` → `tag.py` | `normalised` |

No schedule, matching every other job in this bundle. Verification is its
own job, run on demand like every `verify_*` job.

## Verification

`verification/verify_silver_normalised.py`, job
`verify--silver--normalised--${bundle.target}`, parameters `catalog`,
`source`, `workspace_file_path`. Collects every failure, then asserts (the
`verify_silver_landing.py` shape).

| Check | Rule |
| --- | --- |
| Drift: every Landing column of every `from` table is used, ignored or a platform column; every used column exists | Spec requirement |
| Base row count (+ quarantine) = Landing row count | Parity |
| Base unique on natural key (+ `scd_valid_from_timestamp`) | N1, N6 |
| Bridge row count = non-null elements / set flags in Landing | N2 |
| Every non-null member value exists in its extracted entity | N7 completeness |
| Extracted entity unique on its value (hierarchy/attributes still zero-exception) | N4, N5 |
| Every non-null FK (base, bridge, parent) exists in its target | N10, N5 |
| `sum(value_lineage.row_count)` per value = extracted `row_count` | N9 |
| No null `rdm_proposed_match_key` | N8 |
| Tags present per table (`information_schema.table_tags`) | Tags |
| No null `ingested_timestamp` / `transformed_timestamp` | Timestamps |
| Violating determinant values ≤ `max_violations` | Tolerance |

## CI

A new `pr.yml` job, `normalised-specs`, with no Databricks credentials:

```yaml
- uses: actions/checkout@v4
- uses: astral-sh/setup-uv@v6
- run: uvx check-jsonschema --schemafile docs/normalised-spec/schema.json src/layers/silver/normalised/specs/*.yml
- run: uv run pytest
```

The workflow's `paths` filter gains `docs/normalised-spec/**` and
`tests/**`. Schema validation is CI's job; drift needs the live Landing
tables, so it stays in verification (4c decision). `pytest` in CI is new
for this repo; it runs only `tests/common/` and has no network or
workspace dependency.

# Part 2: airroi

## Context

Source `airroi`; evidence in `profile.json` (pass 1 and pass 2, `dev`,
2026-09-30, `truncated = false` both runs). Precondition met: both Landing
tables carry `ingested_timestamp` (0% null).

| Landing table | Rows | Columns | Natural key |
| --- | --- | --- | --- |
| `market_summary` | 4 | 20 | `_country, _region, _locality, _district` |
| `market_metrics_all` | 48 | 20 | `_country, _region, _locality, _district, date` |

`dev` data is representative: airroi pulls the same four markets in every
target (no row limit), so `prd` differs only in how many SCD2 versions
accumulate.

## Entities

| Entity | Kind | From | Natural key | Rule(s) |
| --- | --- | --- | --- | --- |
| `market_summary` | base | `market_summary` | `_country, _region, _locality, _district` (+ validity) | N1, N6, N10 |
| `market_metrics_all` | base | `market_metrics_all` | `_country, _region, _locality, _district, date` (+ validity) | N1, N6, N10 |
| `country` | extracted | both | `country` | N7, N8 |
| `region` | extracted, parent `country` | both | `region` | N5, N7 |
| `locality` | extracted, parent `region` | both | `locality` | N5, N7 |
| `district` | extracted, parent `locality` | both | `district` | N5, N7 |
| `value_lineage` | lineage | all four domains | `entity, value, source_table, source_column` | N9 |

Expected sizes in `dev`: 2 countries, 3 regions, 4 localities, 1 district
(Cumuruxatiba; `_district` is 75% null in both tables).

## Domains

| Domain | Member columns | Evidence |
| --- | --- | --- |
| `country` | `market_summary._country`, `market_metrics_all._country` | 2 distinct each; `value_overlaps` shared 2 of 2 |
| `region` | `._region` in both | 3 distinct each; shared 3 |
| `locality` | `._locality` in both | 4 distinct each; shared 4 |
| `district` | `._district` in both | 1 distinct each; shared 1 |

`source_name` also overlaps (1 value), but it is a platform column, not a
domain. `date` is part of `market_metrics_all`'s key with 12 distinct
values, a time key rather than a coded attribute, so it is not extracted.

## Repeating groups

None. No column has delimiter rows that look like lists, and there is no
flag family.

## Dependencies

| Table | Determinant → dependent | violating_values | Decision |
| --- | --- | --- | --- |
| `market_summary` | `_locality → _region` | 0 | `locality.parent = region` |
| `market_summary` | `_region → _country` | 0 | `region.parent = country` |
| `market_summary` | `_district → _locality` | 0 | `district.parent = locality` |
| `market_metrics_all` | `_locality → _region` | 0 | same |
| `market_metrics_all` | `_region → _country` | 0 | same |
| `market_metrics_all` | `_district → _locality` | 0 | same |

## Tolerances

None.

## Ignored columns

- `market_summary.market` — a MAP echoing the request's market; checked
  in `dev`: its `country`, `region`, `locality` and `district` entries
  equal the flat key columns on 4 of 4 rows. Keeping it would duplicate
  the key in a non-atomic column.

## Decisions (airroi)

- **The Landing natural key stays whole on the base entities.** `_region`
  and `_country` depend on `_locality`, which is part of the key, so
  strict 2NF would drop them from `market_metrics_all` and key it on
  `_locality, _district, date`. Kept instead: N1 identifies entities by
  their Landing natural key, and the key's internal dependencies are
  already captured by the extracted hierarchy (N5). Dropping key columns
  would also make the key depend on locality names being globally unique,
  which only four markets cannot show. This change clarifies N3 in
  `silver.md` and the baseline spec: dependency splits never remove a
  natural-key column.
- **Distribution metrics stay as MAP columns.** `market_metrics_all`'s
  seven metrics (`average_daily_rate` … `revpar`) are MAPs of fixed keys
  (`avg`, `p25`, `p50`, `p75`, `p90`). They are not a repeating group
  (fixed keys, one value each), so no bridge. Flattening them into columns
  is arguably 1NF but needs a schema attribute v0.1 lacks. Alternative for
  a later minor bump: a `flatten` attribute on base entities.
- **Extracted entities keyed by name alone.** `locality = 'Prado'` is
  unique here, but not in general. If a later market adds a second Prado
  in another region, the `locality` entity gets two rows, verification
  fails, and the spec returns to review, which is the zero-exception rule
  working as designed.

## Risks / Trade-offs

- [Bridges, `unpivot`, attributes and quarantine get no real-data run
  here] → unit tests for their spec rules; acnc (`phase4e`) is their first
  real run, and fixes land there. Accepted by the user.
- [`register_pickle_by_value` may not work for pipeline UDFs on
  serverless] → the airroi run proves it either way; fallback is an inline
  copy of `match_key` in `pipeline.py`, kept equal to the tested one by a
  unit test that imports both.
- [Tags lost on refresh] → the tag step runs after every refresh.
- [A dependency breaks in future data] → verification fails loudly
  (extracted uniqueness), never a silent pick.
- [`pytest` newly in CI] → tests are pure Python with `pyyaml` only; a
  failure blocks the PR, as intended.

## Decisions (framework)

Each becomes a `docs/decision-register.md` entry.

- **airroi as the first source, inside the framework change**, instead of
  a synthetic fixture (needs a throwaway schema) or deferring all real
  runs to acnc (framework unverified until 4e).
- **Pure spec logic separate from Spark transforms**: unit tests with no
  Spark or Java, CI in seconds.
- **Cross-reference checks in `load_spec`**, run by the pipeline at start
  and by the tests; the JSON Schema stays structural only.
- **Platform columns handled by the framework**, not listed per spec.
- **Extracted entities built from base/bridge entities**, not Landing, so
  quarantine exclusions apply consistently.
- **Group, don't pick**: dependency breaks surface as duplicate extracted
  keys caught by verification.
- **Tags by a post-refresh `ALTER … SET TAGS` step**, since the decorator
  has no tags parameter (closes 4c's open question).
- **Match key as a Python UDF sent by value**, so the tested function is
  the one that runs.
- **N3 never splits a natural-key column** (clarification).
- **`pytest` added to CI**, alongside schema validation.

## Migration Plan

1. iac: `phase4d-silver-normalised-airroi-schema` creates
   `silver_normalised_airroi` in `mdp_dev`/`mdp_tst`/`mdp_prd` with
   `silver_landing_airroi`'s grants; applied first.
2. This change's implementation PR deploys to `dev`, runs `silver_airroi`
   then `verify_silver_normalised` for airroi, one at a time.
3. Merge → CI/CD deploys `tst`, then `prd` after approval.

Rollback: revert the PR; the next deploy deletes the pipeline, which drops
its `silver_normalised_airroi` tables (nothing downstream reads them yet).

## Open Questions

None left; both were settled by the `dev` runs (Findings below).

## Findings from the airroi runs in `dev` (implementation)

- **`src/common/**` was glob-included as pipeline source by 12 pipelines**,
  so a `common/` module importing a sibling (`from common import ...`)
  failed `silver_landing_airroi` at initialisation with
  `ModuleNotFoundError`. The glob was a phase3c leftover; removed in its own
  PR (#47) after a validate-only update passed on 11 of the 12 pipelines
  (`airroi_market_summary_ingestion` skipped: paid API). The Spark
  transforms moved to `src/layers/silver/normalised/transforms.py`, since
  they are specific to this layer.
- **Unity Catalog rejects `.` in tag keys** (`INVALID_PARAMETER_VALUE: Tag
  key contains reserved characters`). The 4c names `mdp.layer`,
  `mdp.source_system`, `mdp.entity_kind` became `mdp_layer`,
  `mdp_source_system`, `mdp_entity_kind` (MODIFIED requirement in this
  change's spec delta).
- **Spark set operations reject MAP columns**, and airroi has MAPs, so the
  quarantine split uses joins on violating determinant values, not
  `exceptAll`/`intersectAll`.
- **Extracted entities read Landing rows, not base tables**: attribute
  columns move out of the base entity, so only Landing still has them.
- **PyYAML ships with serverless**: the tag and verification notebooks
  loaded specs with no `environments` block. The pipeline still declares
  `pyyaml` (guardrail: dependencies in bundle config).
- **`register_pickle_by_value` works for pipeline UDFs on serverless**:
  `Vitória da Conquista` got `VITORIA DA CONQUISTA`; no inline fallback.
- **Table ownership suffices for `ALTER MATERIALIZED VIEW … SET TAGS`**: the
  tag step ran as the pipeline's run-as identity with no `APPLY TAG` grant.
- **Results**: `market_summary` 4, `market_metrics_all` 48, `country` 2,
  `region` 3, `locality` 4, `district` 1, `value_lineage` 20; verification
  passed. A rerun with Landing unchanged gave identical row counts and
  row hashes (all columns but `transformed_timestamp`) on all 7 tables, and
  verification passed again.
- **Dev ran on human-identity copies first**, then those were deleted (with
  the user's approval) so the CI/CD SP's `[dev svc_cicd_github]` copies own
  the dev tables, per CLAUDE.md.
- **`RESOURCE_EXHAUSTED` with nothing visibly running**: after a long day
  of runs, every new cluster was refused and the Serverless Starter
  Warehouse would not start. Resolved after the user started and stopped a
  serverless compute from the UI; root cause not confirmed.
