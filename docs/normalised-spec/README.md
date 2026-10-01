# Normalised spec

A **normalised spec** is one YAML file per source,
`src/layers/silver/normalised/specs/{source}.yml`, describing that source's
Silver Normalised entities. It is the only per-source artefact the generic
Silver Normalised pipeline executes. Its format is defined by the
**normalised spec schema**, [`schema.json`](schema.json) (v0.2). Layer
definition and rules N1–N10: [`silver.md`](../medallion/silver.md#silver-normalised).

"Spec" is always qualified as "normalised spec", since openspec has its
own `specs/`.

## Why a spec

Deciding which columns share a domain, which attributes depend on which,
and where a list hides a repeating group needs judgement, but only once per
source. The spec captures that judgement at design time: an agent proposes
it from profiling evidence, a person reviews it in the source's propose PR,
and the pipeline replays it deterministically on every refresh. No LLM runs
at pipeline run time.

## Example

acnc, column names illustrative until profiled:

```yaml
source_system: acnc
base_entities:
  charity_register:
    from: silver_landing_acnc.charity_register
    natural_key: [abn]
    history: scd2
    columns: [charity_legal_name, charity_size, date_established]
    extracted:
      address_country: country
      address_state: state
bridge_entities:
  charity_register_operating_country:
    from: silver_landing_acnc.charity_register
    parent: charity_register
    explode: {column: operating_countries, split: ";"}
    extracted: country
  charity_register_beneficiary:
    from: silver_landing_acnc.charity_register
    parent: charity_register
    unpivot: {columns_like: "beneficiary_%", keep_when: "Y"}
    extracted: beneficiary_type
extracted_entities:
  country:          {}
  state:            {parent: country}
  beneficiary_type: {}
ignored_columns: []
```

## Attributes

| Attribute | Required | Meaning |
| --- | --- | --- |
| `source_system` | yes | Suffix of the `silver_landing_{source}` schema the spec reads from; also the `silver_normalised_{source}` schema it writes to |
| `base_entities` | yes | Base entities, keyed by table name; each keeps its Landing table's name |
| `base_entities.{name}.from` | yes | Landing table, as `silver_landing_{source}.{table}` |
| `base_entities.{name}.natural_key` | yes | Natural key columns, placed first (N1) |
| `base_entities.{name}.history` | no | `scd2` keeps `scd_valid_from_timestamp`, `scd_valid_to_timestamp` and `is_current` (N6); omit for none |
| `base_entities.{name}.columns` | yes | Attributes kept on the entity; every one must exist in the Landing table |
| `base_entities.{name}.extracted` | no | Map of column → extracted entity. The column stays as a foreign key; its dependent attributes move to the extracted entity (N10) |
| `bridge_entities` | no | Bridge entities (N2), keyed by table name `{parent}_{attribute}` |
| `bridge_entities.{name}.from` | yes | Landing table holding the repeating group |
| `bridge_entities.{name}.parent` | yes | Base entity (a key of `base_entities`) whose natural key the bridge carries |
| `bridge_entities.{name}.explode` | one of | `{column, split}`: one row per element of a delimited list |
| `bridge_entities.{name}.unpivot` | one of | `{columns_like \| columns, keep_when}`: one row per column in the family whose value equals `keep_when`; the element is the column name. The family is selected by a SQL LIKE pattern (`columns_like`) or, when its columns share no name pattern, an explicit list (`columns`, v0.2) |
| `bridge_entities.{name}.extracted` | no | Extracted entity the element belongs to; the element stays as a foreign key (N10) |
| `extracted_entities.{name}.parent` | no | Parent level in a hierarchy (N5); the entity carries the parent's key as a foreign key |
| `extracted_entities.{name}.attributes` | no | Extra columns that depend on the value, e.g. `country_code` (N7, N10) |
| `dependency_tolerance` | no | List of `{entity, determinant, dependent, max_violations}`: a per-case exception to N4's zero-exception rule. Rows for violating determinant values go to `{entity}_quarantine`. Each entry needs its reason in the source change's `design.md` |
| `ignored_columns` | yes | Landing columns deliberately left out, as `table.column`. Every Landing column the spec reads is either used or listed here, which is what the drift check verifies |

**One block per entity kind.** `base_entities`, `bridge_entities` and
`extracted_entities` match the three `mdp_entity_kind` tag values. A
bridge's key is its parent's natural key plus the element; it declares
exactly one of `explode` or `unpivot`. Bridges are explicitly revisitable:
if they prove unnecessary, the `bridge_entities` block is removed (a major
version bump, below).

**Extracted entities** are named after their domain, singular. An entity
listed in `extracted_entities` collects every value mapped to it through a
base entity's `extracted` map or a bridge's `extracted`, across all tables
and all SCD2 versions (N7).

## Platform columns

A spec never lists the platform columns, and the drift check never counts
them; the generic pipeline carries them itself:
`scd_valid_from_timestamp`, `scd_valid_to_timestamp`, `is_current`,
`source_name`, `source_file_name`, `ingested_timestamp`,
`transformed_timestamp`.

| Table | Platform columns |
| --- | --- |
| Base | Validity columns when `history: scd2`; `source_name`, `source_file_name`, `ingested_timestamp` passed through; `transformed_timestamp` restamped |
| Bridge | Parent's validity columns when the parent is `scd2` (N6); `ingested_timestamp` passed through; `transformed_timestamp` restamped |
| Extracted, `value_lineage` | `ingested_timestamp` = `max()` of the aggregated rows; `transformed_timestamp` restamped |
| `{entity}_quarantine` | Same columns as its base entity |

A Landing table with validity columns needs `history: scd2` on its base
entity, or the pipeline fails.

## What the pipeline builds

The generic pipeline, `src/layers/silver/normalised/pipeline.py`, builds one
materialized view per entity:

- **Base**: natural key, `columns`, then the `extracted` foreign keys not
  already listed, then platform columns.
- **Bridge**: parent natural key and validity, then one element column
  named after the bridge's attribute (its name without `{parent}_`).
  `explode` splits on the literal delimiter and keeps elements exactly as
  split, with no trimming.
- **Extracted**: `{entity}` (the value, unchanged), `{parent}` when set,
  `attributes`, `rdm_proposed_match_key`, `row_count`, timestamps. Rows are
  grouped by value, parent and attributes, never picked: if new data breaks
  a dependency, the value gets two rows and verification fails.
- **`value_lineage`**: `entity`, `value` (as string), `source_table`,
  `source_column`, `row_count`, timestamps.
- **`{entity}_quarantine`**: for a base entity with a `dependency_tolerance`,
  the rows whose determinant value violates it.

A parent or an attribute is read from the same Landing row as the member
column: the parent from the one column of that base entity mapped to the
parent entity.

## Cross-reference checks

The pipeline refuses to start, and the unit tests fail, when a spec breaks
a rule the schema cannot express (`src/common/normalised_spec.py`):

- every `from` is in `silver_landing_{source_system}`
- entity names are unique across blocks; none is `value_lineage` or ends
  in `_quarantine`
- a bridge's `parent` is a base entity with the same `from`
- every extracted target is declared, and every declared extracted entity
  has a member column
- `parent` exists and has no cycle
- a base entity holding a member of an entity with a `parent` has exactly
  one column mapped to that parent
- an entity with a `parent` or `attributes` has no bridge members
- a tolerance names a base entity that uses both its columns
- no column is both used and ignored

Three of these are **v0.1 limits**, relaxed by a minor version bump when a
real source needs it: a bridge sharing its parent's `from`, exactly one
parent column per base entity, and no bridge members for an entity with a
`parent` or `attributes`.

## Extending the format

- Add an attribute only when a real source needs it, as a **minor** version
  bump (e.g. `0.1` → `0.2`) of `schema.json`, in the openspec change of the
  source that needs it, with this README updated in the same PR.
- History: v0.2 added `unpivot.columns` (acnc's purpose and beneficiary
  flags share no name prefix).
- Removing or renaming an attribute is a **major** version bump and must
  migrate every existing spec in the same change.
- The `bridge_entities` block is explicitly revisitable after the first
  sources.

## Adding a source

Each source follows CONTRIBUTING.md's two-PR flow (propose, then
implement); these are the Silver Normalised specifics.

0. **Precondition.** If the source's Silver Landing tables lack
   `ingested_timestamp`, retrofit bronze in its own change first (see
   NAMING.md, "Platform-added timestamp columns").
1. **Branch** `feature/silver-normalised-{source}`.
2. **Profile** on `dev` with the standard profiling job,
   `profile_silver_normalised` (pass 1, then pass 2 with the candidate
   dependency pairs); save the run outputs as `profile.json` in the openspec
   change folder.
3. **Propose** with the `silver-normalised-propose` skill on Opus. It
   follows [the prompt template](../templates/silver-normalised-propose.prompt.md)
   and writes the normalised spec plus the openspec change, with `design.md`
   from [the skeleton](../templates/silver-normalised-design.md).
4. **PR 1: review and merge.** The real design review: entities, domains,
   splits, tolerances. Edit the spec in the PR if needed.
5. **Implement** on Sonnet: the `silver_normalised_{source}` schema and
   grants in `demo-databricks-iac` first (cross-repo dependency), then the
   bundle resources pointing the generic pipeline at the spec, the
   orchestrating `silver--{source}` job, verification, and the source's
   "Consumed by Silver Normalised" line in `docs/registers/data-sources.md`.
6. **Validate, deploy to `dev`, verify**: base row parity (with
   quarantine), bridge element counts, extracted value completeness, FK
   integrity, no Landing drift.
7. **PR 2: merge, then archive** the openspec change.
8. **rdm picks up** the newly tagged extracted entities in its own process.

When a Landing table gains or changes columns, the drift check fails and
the source goes back to step 2.
