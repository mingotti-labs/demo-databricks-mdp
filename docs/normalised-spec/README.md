# Normalised spec

A **normalised spec** is one YAML file per source,
`src/layers/silver/normalised/specs/{source}.yml`, describing that source's
Silver Normalised entities. It is the only per-source artefact the generic
Silver Normalised pipeline executes. Its format is defined by the
**normalised spec schema**, [`schema.json`](schema.json) (v0.1). Layer
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
| `bridge_entities.{name}.unpivot` | one of | `{columns_like, keep_when}`: one row per column in the family whose value equals `keep_when`; the element is the column name |
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

## Extending the format

- Add an attribute only when a real source needs it, as a **minor** version
  bump (`0.1` → `0.2`) of `schema.json`, in its own openspec change, with
  this README updated in the same PR.
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
