## Why

acnc proved the bronze full pattern (`correct-platform-timestamps`, PR #92):
snapshot Auto CDC that leaves per-load columns out of the snapshot, and a Silver
Landing that reads the SCD2 change feed. The other full-load sources still run
the old shape, so their timestamps are wrong in the way acnc's were, and the
platform carries two shapes side by side.

Findings from the code and from dev and prd (read-only, 2026-10-23):

| Source | Raw stamps `ingested_timestamp` | SCD2 snapshot | Landing |
|---|---|---|---|
| ungm, nsw_spatial | no | raw directly, nothing per-load in it | materialized view, `land()` restamps every row each run |
| iso, geonames | yes | a view that adds `current_timestamp()` as `transformed_timestamp`; both columns "untracked", so every current row is rewritten each run | materialized view, same restamp |
| acnc | yes | done | done |

So for ungm and nsw_spatial the SCD2 table is already correct; only Landing is
wrong. iso and geonames have acnc's exact bug. Their raw tables do not need
`ingested_timestamp` for the pattern to work; Landing takes it from `__START_AT`.

## What Changes

- **Sources**: ungm, iso, geonames, nsw_spatial (8 Landing tables, 8 SCD2
  tables). Out of scope: airroi (paid API, `ci_auto_run` off, needs a deliberate
  dev-only run), neon (raw is an upserted table, a different pattern), clickstream
  (append-only), all SCD1 tables.
- **iso, geonames bronze**: the SCD2 snapshot view drops `ingested_timestamp`;
  the `current_timestamp()` stamping and `track_history_except_column_list` go;
  `subdivision_codes_deduped` stops stamping. `delta.enableChangeDataFeed` on
  every SCD2 table.
- **ungm, nsw_spatial bronze**: only `delta.enableChangeDataFeed` on the SCD2
  table.
- **Silver Landing, all 8 tables**: a streaming table over the SCD2 change feed,
  `ingested_timestamp = __START_AT` (same code as acnc's Landing).
- **Reset task per unit** (one parameterised notebook): drops the old Landing
  materialized views, and for iso and geonames also their SCD2 tables (new load).
  ungm and nsw_spatial keep their SCD2 tables and history.
- **Verification**: one `verify_bronze` notebook and one job taking `source`,
  driven by a spec file per source (raw table, key, SCD tables, quarantine),
  replacing five per-source jobs and ten notebooks. Every `run_<unit>` job gets
  acnc's opt-in gate: a `verify` parameter, default `"false"`, a condition task,
  and `silver` depending on `bronze` as well. The silver Landing verification is
  gated the same way.
- **Retries off**: both retry settings `"0"` on the other 27 pipelines (20 main,
  7 patterns bundle), moved here from #92 so it did not run every unit in prd.
- **Docs**: NAMING.md, patterns register, `design_patterns.yml`, CLAUDE.md,
  decision register, `data-sources.md`; the bronze full pattern is stated as the
  pattern for every full-load source.

## Capabilities

### New Capabilities
- `bronze-verification`: one parameterised, opt-in bronze verification.

### Modified Capabilities
- `platform-timestamps`: every full-load source follows the bronze full pattern
  and a change-feed Landing (added requirements; the acnc change adds the base).
- `pipeline-per-layer`: unchanged structure; Landing tables become streaming tables.

## Drops that need approval (dev and prd; there is no tst)

| Table | dev rows | prd rows | closed versions (dev / prd) |
|---|---|---|---|
| Landing: `silver_landing_ungm.unspsc_public` | 12,721 | 13,511 | |
| Landing: `silver_landing_iso.country_codes`, `subdivision_codes` | 249, 6,250 | 249, 6,250 | |
| Landing: `silver_landing_geonames.country_info`, `admin1_codes`, `admin2_codes`, `cities` | 252, 3,865, 47,641, 236,415 | 252, 3,865, 47,642, 236,716 | |
| Landing: `silver_landing_nsw_spatial.property` | 500 | 10,007 | |
| SCD2: `bronze_iso_publish.country_codes_scd2`, `subdivision_codes_scd2` | 249, 6,250 | 249, 6,250 | 0 / 0 |
| SCD2: `bronze_geonames_publish.country_info_scd2`, `admin1_codes_scd2`, `admin2_codes_scd2` | 252, 3,865, 47,641 | 252, 3,865, 47,642 | 0 / 0 |
| SCD2: `bronze_geonames_publish.cities_scd2` | 236,415 | 236,716 | 0 / **84** |

Landing tables hold no history of their own (rebuilt from the SCD2 table). The
only history lost is **84 closed `cities` versions in prd**. ungm and nsw_spatial
SCD2 tables are not dropped (prd nsw_spatial keeps its 7 closed versions).

## Model

Sonnet to implement: it repeats the acnc pattern per source. The verification
spec format is the only new design; it is small.

## Impact

- Merging the implement PR makes CI run all five units in prd (acnc, ungm, iso,
  geonames, nsw_spatial; airroi is opted out): about 45 minutes, the #88
  precedent, plus the prd approval gate. The 27 pipeline files changed for
  retries select every unit regardless.
- Dev is verified one unit at a time (Free Edition runs one workload at once),
  with verification on for the first run of each.
- Verification is off by default in CI, including prd.
- Table count: the SCD2 and Landing tables are recreated, not added.
