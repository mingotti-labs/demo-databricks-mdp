## Context

See proposal.md - Why. Identical shape to `phase4a-silver-landing`'s
onboarding: every source table already has a keyed, uniquely-identified
SCD2 object in Bronze Publish (confirmed during `phase3i`/`phase3j`'s own
implementation), so this is a mechanical application of the existing
`land()` helper and pipeline pattern, not new design work.

## Goals / Non-Goals

**Goals:**
- All six ISO/GeoNames Bronze Publish SCD2 entities land in Silver as
  source-aligned Materialized Views, using the existing `land()` helper
  unchanged
- `verify_silver_landing` extended to cover all six new tables

**Non-Goals:**
- Any change to `docs/medallion/silver.md` or `src/common/silver_landing.py`
  — both are already source-agnostic and need no edits
- Silver Normalised/Domain/Marts for these sources — out of scope, same as
  every other source's Silver Landing onboarding

## Decisions

**SCD2 only, since neither source has a SCD1 variant.** ISO and GeoNames
are both SCD2-only in Bronze Publish (`phase3i`/`phase3j`'s own scope
decision) — `land(..., scd2=True)` for all six tables, no SCD1 branch to
handle.

**Table names use the entity's logical name, dropping the `_scd2` suffix**
— `country_codes`, `subdivision_codes`, `country_info`, `admin1_codes`,
`admin2_codes`, `cities` — same convention `silver.md`'s naming section
already establishes (e.g. `unspsc_public`, not `unspsc_public_scd2`).

**Natural keys, one Silver Landing pipeline per source:**

| Table | Bronze Publish source | Natural key(s) |
|---|---|---|
| `country_codes` (iso) | `country_codes_scd2` | `country_code_alpha2` |
| `subdivision_codes` (iso) | `subdivision_codes_scd2` | `subdivision_code`, `language_code`, `subdivision_name` |
| `country_info` (geonames) | `country_info_scd2` | `iso_alpha2` |
| `admin1_codes` (geonames) | `admin1_codes_scd2` | `code` |
| `admin2_codes` (geonames) | `admin2_codes_scd2` | `code` |
| `cities` (geonames) | `cities_scd2` | `geonameid` |

All six keys were already confirmed unique against real data during
`phase3i`/`phase3j`'s own implementation — no new uniqueness risk here,
Silver Landing just reads the same already-deduplicated Bronze Publish
object.

**`ingested_timestamp` propagates unchanged, same as AirROI's.** Both
ISO's and GeoNames' Bronze Publish SCD2 objects already carry
`ingested_timestamp` (stamped at their own `_raw` layer) — `land()` never
touches this column, so it passes through automatically. This is the
second and third source (after AirROI) where `verify_silver_landing.py`'s
non-null check applies.

## Risks / Trade-offs

None beyond the standard "confirmed via a real pipeline run" discipline —
mechanical application of an existing, already-verified pattern to two
already-verified Bronze Publish sources.

## Migration Plan

Depends on `demo-databricks-iac`'s
`phase4b-silver-landing-iso-geonames-schemas` landing first. Deploy to
`dev`, verify via the extended `verify_silver_landing` job, then promote to
`tst`/`prd`. Rollback: remove the two pipeline resources and six source
files from the bundle; full-refresh only, no destructive state involved.
