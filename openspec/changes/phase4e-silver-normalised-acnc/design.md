## Context

Source `acnc` (ACNC Charity Register); evidence in `profile.json`: pass 1
and pass 2 on the **full** dataset in `dev` (2026-10-01, `truncated =
false` both runs), plus the same dependency checks run read-only on prd.

| Landing table | Rows | Columns | Natural key |
| --- | --- | --- | --- |
| `charity_register` | 65,802 (10 closed SCD2 versions) | 75 | `ABN` |

**Precondition, handled inside this change** (user decision): Landing
lacks `ingested_timestamp`. The bronze retrofit is this change's first
implementation task group, verified before the Normalised pipeline is
deployed. `docs/normalised-spec/README.md` step 0 and the prompt template
are amended to allow "its own change, or the first tasks of the source's
change".

**Why the full dataset.** `dev`/`tst` pulled a 500-row sample
(`acnc_row_limit`). Profiled on the sample, Postcode → State had 0
violations; on the full data it has 157. This change sets `dev` to the full
dataset (`databricks.yml`, already in the propose PR so PR CI deployed it
under the CI service principal) and re-profiled. Dev and the prd cross-check
agree within one or two values on every pair.

Dev ownership (step 0 of this source): bronze acnc was already owned by the
CI service principal; the human-owned `silver_landing_acnc` copy and two
empty human bronze copies were deleted by the user before profiling.

## Entities

| Entity | Kind | From | Natural key | Rule(s) |
| --- | --- | --- | --- | --- |
| `charity_register` | base | `charity_register` | `ABN` (+ validity) | N1, N6, N10 |
| `charity_register_operating_state` | bridge | 8 `Operates_in_*` flags | `ABN` + validity + `operating_state` | N2 |
| `charity_register_operating_country` | bridge | `Operating_Countries` | `ABN` + validity + `operating_country` | N2 |
| `charity_register_purpose` | bridge | 12 purpose flags | `ABN` + validity + `purpose` | N2 |
| `charity_register_beneficiary` | bridge | 29 beneficiary flags | `ABN` + validity + `beneficiary` | N2 |
| `address_type`, `locality`, `state`, `postcode`, `country`, `charity_size`, `financial_year_end` | extracted | base columns | the value | N7, N8 |
| `operating_state`, `purpose`, `beneficiary` | extracted | bridge elements | the value | N7, N8 |
| `value_lineage` | lineage | all extracted | `entity, value, source_table, source_column` | N9 |

## Domains

| Domain | Member columns | Evidence |
| --- | --- | --- |
| `country` | `Country`, bridge `operating_country` | `Country`: 21 distinct (`Australia` 55,361, `AUSTRALIA` 3,129, `Austria`, `Australia.`, a phone number); `Operating_Countries`: ISO3 codes. Same meaning, different spellings: rdm's job |
| `state` | `State` | 22 distinct, variants of 8 states |
| `postcode` | `Postcode` | 2,566 distinct, max length 19 |
| `locality` | `Town_City` | 8,050 distinct (`Sydney`, `MELBOURNE`…); named `locality` by meaning, as in airroi |
| `charity_size` | `Charity_Size` | 3 distinct |
| `financial_year_end` | `Financial_Year_End` | 90 distinct (`30-Jun` 44,936) |
| `address_type` | `Address_Type` | 1 distinct (`Business`); N7 applies even to a single value |
| `operating_state` | bridge element | the 8 `Operates_in_*` column names |
| `purpose` | bridge element | the 12 purpose column names |
| `beneficiary` | bridge element | the 29 beneficiary column names |

## Repeating groups

| Bridge | Landing column(s) | explode / unpivot | Evidence |
| --- | --- | --- | --- |
| `charity_register_operating_country` | `Operating_Countries` | explode, literal `", "` | 2,100 rows contain `,`; top values `AUS`, `AUS, NZL`; splitting on `", "` keeps elements clean without trimming |
| `charity_register_operating_state` | `Operates_in_ACT` … `_WA` | unpivot `columns_like: "Operates_in_%"`, `keep_when: Y` | 8 columns, each 1 distinct value `Y` |
| `charity_register_purpose` | 12 columns | unpivot `columns` (v0.2) | 1 distinct value `Y` each; no shared name prefix |
| `charity_register_beneficiary` | 29 columns | unpivot `columns` (v0.2) | 1 distinct value `Y` each; no shared name prefix (`Adults`, `LGBTIQA+`, `animals`…) |

## Dependencies

Full dev data; prd cross-check in brackets.

| Table | Determinant → dependent | violating_values | Decision |
| --- | --- | --- | --- |
| `charity_register` | `State → Country` | 10 (10) | no hierarchy |
| `charity_register` | `Postcode → State` | 157 (157) | no hierarchy |
| `charity_register` | `Town_City → State` | 481 (482) | no hierarchy |
| `charity_register` | `Postcode → Town_City` | 1,723 (1,721) | no hierarchy |
| `charity_register` | `Town_City → Postcode` | 786 (787) | no hierarchy |
| `charity_register` | `Postcode → Country` | 732 (732) | no hierarchy |
| `charity_register` | `Town_City → Country` | 754 (753) | no hierarchy |

Postcode → State on prd, examined: of 157, 131 are case/spacing variants
(`2000`: `NSW`, `nsw`); 26 remain ignoring case, a mix of genuine
cross-border postcodes (`0872` NT/SA/WA, `2620` NSW/ACT, `2540` NSW/ACT,
`4825` QLD/NT) and entry errors (`2000` with `VICTORIA & NSW`). Splitting
would force Silver to choose; N4 keeps them all on the base entity as
independent foreign keys.

## Tolerances

None.

## Ignored columns

None: all 69 non-platform Landing columns are used.

## Decisions (acnc)

- **No address hierarchy.** Every address dependency breaks at full scale
  (table above). Alternative: tolerances with quarantine; rejected, the
  violations are hundreds of values and mostly spelling variants, which is
  rdm's job, not Silver's.
- **`Operates_in_*` elements are column names**, so a separate
  `operating_state` entity holds `Operates_in_NSW`…, not `state`.
  Alternative: strip the prefix so elements join `state` (`NSW`); needs a
  new schema attribute, deferred until a second source needs it.
- **`Operating_Countries` joins `country`** with `Country`, by meaning,
  though one is ISO3 (`AUS`) and the other a name (`Australia`). rdm
  matches both to ISO 3166.
- **Kept on the base entity, not bridged**: `Address_Line_1..3` (ordered
  parts of one address, not a set); `Other_Organisation_Names` (mixed `,`
  and `;` delimiters, and names that contain commas, so splitting would
  corrupt values); `PBI`, `HPC` (two independent flags, not a family).
- **Dates stay strings** (`Registration_Date`, `Date_Organisation_Established`,
  `dd/mm/yyyy`): values unchanged; typing belongs to a later layer.

## Framework corrections in this change

Found while proposing acnc; each changes the framework for every source.

1. **Schema v0.2: `unpivot.columns`**, an explicit list for flag families
   with no shared name pattern (planned in 4c's findings). The pipeline,
   drift check and verification read either `columns_like` or `columns`.
2. **Null is not a value when resolving a parent** (user decision). For an
   extracted entity with a `parent`, a value seen with one recorded parent
   and some blanks gets one row with that parent; blanks no longer create a
   second row. Two different recorded parents still give two rows and fail
   verification. This matches profiling, whose `count(DISTINCT …)` already
   ignores nulls, so pass 2 and the pipeline now agree.
3. **`ingested_timestamp` checked on current rows only.** SCD2 versions
   closed before a source's retrofit keep a null `ingested_timestamp`
   (user decision: `max()` downstream ignores them). Verification requires
   it non-null where `is_current` (or on every row of a non-SCD2 base
   entity). acnc has 10 such closed versions in `dev`, 0 in `tst`/`prd`.
4. **Pass 2 on full data.** For a source whose `dev` is row-limited, the
   dependency evidence must come from the full dataset: lift the `dev`
   limit if the source allows it (acnc), otherwise run pass 2 read-only on
   prd. The prompt template and README step 2 say so.

## Retrofit (bronze `ingested_timestamp`)

- `charity_register_raw` stamps `ingested_timestamp` (airroi pattern).
- `charity_register_valid` passes it through; `charity_register_scd2` lists
  it, and `transformed_timestamp` (stamped in the valid view, per
  NAMING.md), in `track_history_except_column_list`. `charity_register_scd1`
  carries both, updated in place.
- Silver Landing needs no code change (`land()` keeps every column);
  `verify_silver_landing.py` adds `acnc` to the sources expected to carry it.
- Adding a column to an existing snapshot-CDC target: verified in `dev`
  first. **No full refresh happened** — `charity_register_scd2`'s earliest
  `__START_AT` is unchanged (2026-09-22, predating the retrofit run), and
  its 10 pre-existing closed versions are intact, now with a null
  `ingested_timestamp` as designed. Every current row (65,792 of 65,802)
  got the column populated; `current_without_ts = 0`.
- Silver Landing propagated the retrofit unchanged, confirmed by direct
  query (same 65,802/10/0 split as bronze): row count parity, provenance,
  `is_current` derivation and the narrowed `ingested_timestamp` check all
  pass for acnc. The shared `verify_silver_landing.py` job could not be
  run end-to-end in `dev` as the SP — it also checks `neon`, whose dev
  table (`silver_landing_neon.customers`) is still human-owned, the same
  class of issue found for airroi in `phase4d` and acnc itself at this
  change's step 0. Not fixed here (out of scope); acnc's own checks were
  confirmed directly instead.

## Risks / Trade-offs

- [Bridges, `unpivot` and the null-parent rule get their first real run
  here] → that is this change's purpose; verification covers bridge element
  counts and extracted uniqueness.
- [`operating_state` duplicates `state`'s meaning] → accepted for v0.2; a
  prefix-strip attribute can merge them later.
- [prd Landing for acnc has never been built] → the `silver_acnc` job runs
  Landing first; tst/prd runs are listed in the migration plan.
- [Full acnc pull in `dev`] → free CKAN API, ~66 page requests; the pull
  completed in minutes.

## Migration Plan

1. iac: `phase4e-silver-normalised-acnc-schema` creates
   `silver_normalised_acnc` with Silver Landing's grants; applied first.
2. Implementation PR deploys `dev`; run the SP chain by ID: bronze
   ingestion → SCD → `silver_acnc` (landing → normalised → tag) →
   verification.
3. Merge → CI/CD deploys `tst`, then `prd` after approval; run the same SP
   chain in each, one at a time.

Rollback: revert; the next deploy removes the Normalised pipeline (its
tables are dropped) and the bronze column change.
