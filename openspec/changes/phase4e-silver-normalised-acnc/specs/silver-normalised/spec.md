## MODIFIED Requirements

### Requirement: Extracted entity columns
Each extracted entity SHALL have, in order: the value column named after
the entity; the parent entity's value column when it has a `parent`; its
`attributes`; `rdm_proposed_match_key`; `row_count`; `ingested_timestamp`;
`transformed_timestamp`. It SHALL be built from the same non-quarantined
Landing rows as its base entities and from its bridge entities, never
choosing one of several recorded values. A blank (null) parent SHALL NOT
count as a value: a value recorded with exactly one non-null parent and
some null parents SHALL get one row with that parent, and a value recorded
only with null parents SHALL get one row with a null parent.

#### Scenario: Dependency broken by new data
- **WHEN** a later refresh brings locality `Prado` with a second region
- **THEN** the `locality` entity holds two `Prado` rows and verification
  fails on extracted-key uniqueness

#### Scenario: Blank parent alongside a recorded one
- **WHEN** postcode `2000` appears with state `NSW` on two rows and with a
  null state on one row
- **THEN** the `postcode` entity holds one `2000` row with state `NSW` and
  a `row_count` of 3

### Requirement: Generic verification
A verification job, `verify--silver--normalised--${bundle.target}`, SHALL
check one source at a time against its spec and fail listing every broken
check: drift (every Landing column used, ignored or a platform column,
and every used column present), base parity with quarantine, natural-key
uniqueness, bridge element counts, extracted value completeness,
extracted-key uniqueness, foreign-key integrity, `value_lineage` totals,
non-null match keys and timestamps, tags, and tolerance limits.
`ingested_timestamp` SHALL be checked non-null only on current rows of
SCD2 base entities (and on every row of other base entities), since SCD2
versions closed before a source's `ingested_timestamp` retrofit keep it
null.

#### Scenario: Clean source
- **WHEN** verification runs for a source whose tables match its spec and
  Landing
- **THEN** the job succeeds and reports the number of tables checked

#### Scenario: Version closed before the retrofit
- **WHEN** a base entity has a closed SCD2 version with a null
  `ingested_timestamp` and every current row has one
- **THEN** the timestamp check passes

### Requirement: Standard profiling evidence
A standard profiling job SHALL profile one source's Silver Landing tables,
across all SCD2 versions, and return the result as a single JSON document
without writing to any table or volume. Without dependency pairs it SHALL
return, per column, type, null %, distinct count, top 20 values with
counts, max length and delimiter presence, plus distinct-value overlap
counts between string columns across the source's tables. Given a list of
dependency pairs, it SHALL return the number of violating determinant
values per pair. Dependency evidence SHALL come from the source's full
dataset: when `dev` is row-limited, either the limit is lifted for `dev`
or the dependency checks run read-only against `prd`.

#### Scenario: First profiling pass
- **WHEN** the profiling job runs for `acnc` with no dependency pairs
- **THEN** it returns JSON with column statistics for every column of every
  `silver_landing_acnc` table and the cross-table value overlaps, and no
  table or volume is written

#### Scenario: Dependency pass
- **WHEN** the profiling job runs with a dependency pair whose determinant
  maps to more than one dependent value for 3 determinant values
- **THEN** it reports 3 violating values for that pair

#### Scenario: Row-limited source
- **WHEN** a source's `dev` holds a 500-row sample of a 66k-row dataset
- **THEN** its proposed splits rest on dependency checks over the full
  dataset, not the sample

### Requirement: Repeating groups become bridge entities (N2)
A delimited list column, or a family of numbered or flag columns, SHALL be
flattened into a bridge entity named `{parent}_{attribute}`, keyed by the
parent's natural key plus the element. A bridge's row count SHALL equal
the number of non-null list elements (or flags set to their "true" value)
in the Landing table. A flag family SHALL be selected by a name pattern or,
when its columns share none, by an explicit column list.

#### Scenario: Delimited list
- **WHEN** a charity's Landing row has `operating_countries = 'AU;NZ;FJ'`
- **THEN** the bridge `charity_register_operating_country` holds three rows
  for that charity, one per country value

#### Scenario: Flag family without a shared prefix
- **WHEN** a spec lists `Adults`, `Children` and `Youth` as one family and
  a charity has `Y` in `Adults` and `Youth`
- **THEN** the bridge holds two rows for that charity, `Adults` and `Youth`
