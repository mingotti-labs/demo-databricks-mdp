## Why

`acnc-two-pipelines` made acnc one pipeline per layer but left the baseline
specs and silver docs describing the old layout: `silver-normalised` still
requires a `silver--{source}` orchestrating job and a separate
`silver--normalised--{source}` pipeline, and `pipeline-per-layer` only
speaks of "migrated" sources. Every other source's current layout is then
neither clearly a defect nor clearly pending work. This change makes one
pipeline per layer the rule for every source and lists, inside each
affected requirement, the sources that still need refactoring, plus the
agreed exceptions, so the specs carry no ambiguity.

## What Changes

- **`pipeline-per-layer`**: the layout becomes the rule for every source
  (renamed "One pipeline per layer per source"), with:
  - **Exception**: neon's bronze layer keeps two pipelines, because its
    ingestion is managed Lakeflow Connect, which cannot hold SCD code.
  - **Exempt reference variants**: clickstream's seven non-canonical Auto
    Loader pipelines and its SQL SCD pipeline, and neon's SQL SCD pipeline
    and SQL SCD2 merge job, are outside the rule.
  - **Sources pending refactor**, listed per requirement: airroi, ungm,
    iso, geonames, nsw_spatial, clickstream, neon (silver display names,
    bronze merges, airroi's wrapper job, verify job names).
- **Clickstream's seven non-canonical Auto Loader pipelines renamed
  `template`** (display names only): e.g.
  `bronze--template--autoloader--python--rescue--<target>`. The Auto Loader
  pipeline feeding `bronze_clickstream_publish` (`clickstream_autoloader`)
  and both SCD pipelines keep `clickstream`.
- **`silver-normalised`**: the generic pipeline runs inside the source's
  silver pipeline; tags are a task of `run_<source>`; Landing and
  Normalised share one pipeline graph instead of a chaining job. airroi is
  listed as pending.
- **`ci-affected-units`**: two scenarios used the deleted `silver_acnc` job
  as their example; they now use jobs that exist.
- Docs: `docs/medallion/silver.md` (Orchestration, Materialisation),
  `docs/normalised-spec/README.md` (onboarding step 5), NAMING.md
  (template naming, neon exception), CLAUDE.md (clickstream entry).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `pipeline-per-layer`: rule for every source, exceptions, exempt
  reference variants, sources pending refactor.
- `silver-normalised`: generic pipeline placement, tag step and
  orchestration follow one pipeline per layer; airroi pending.
- `ci-affected-units`: scenario examples no longer name `silver_acnc`.

## Model

Opus to propose (it fixes a gap in the previous proposal and records
exceptions); Sonnet to implement (docs and seven display-name changes).

## Impact

- Specs and docs only, plus display names of seven clickstream reference
  pipelines (in-place rename, no resource key, table or schema change).
- No data, schema, grant or iac change. The refactors themselves are
  follow-up changes, one per source, each removing its entries from the
  pending lists.
