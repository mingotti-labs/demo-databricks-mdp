## Context

See proposal.md - Why. Inventory (bundle, 2026-10-20): acnc compliant;
airroi 2 bronze + 2 silver pipelines and a `silver_airroi` job; ungm, iso,
geonames, nsw_spatial 2 bronze + 1 silver (displayed
`silver--landing--<source>`); neon a Lakeflow Connect ingestion pipeline,
Python and SQL SCD pipelines and a SQL SCD2 merge job; clickstream eight
Auto Loader pipelines (only `clickstream_autoloader` is run) and Python
and SQL SCD pipelines. Silver Landing reads only the Python SCD outputs
(`bronze_clickstream_publish.web_events_scd1`, `bronze_neon_publish.*`).

## Goals / Non-Goals

**Goals:** specs say exactly which sources comply, which are excepted,
which are exempt and which are pending; docs match.

**Non-Goals:** refactoring any source (one follow-up change each, which
also removes the source from the pending lists).

## Decisions

### D1. Pending lists live inside each requirement
Each affected requirement states the rule, then **Exceptions**, **Exempt
reference variants** where relevant, and **Sources pending refactor**. A
reader of one requirement sees its whole compliance picture; a refactor
change edits exactly the requirements it makes true. (User's direction.)

### D2. neon's bronze is an exception, not pending
Its ingestion is a managed Lakeflow Connect pipeline (`ingestion_definition`
in the bundle), which accepts no transformation code, so SCD stays in
`neon_scd_modeling_python`. (User decision, 2026-10-20.)

### D3. Reference variants are exempt; clickstream's Auto Loader ones are named `template`
Exempt: clickstream's seven non-canonical Auto Loader pipelines and
`clickstream_scd_modeling_sql`; neon's `neon_scd_modeling_sql` and
`neon_scd2_merge_sql`. The seven Auto Loader variants are displayed with
the source system `template` so the workspace no longer suggests they are
part of clickstream's flow; the Auto Loader pipeline that feeds
`bronze_clickstream_publish` (`clickstream_autoloader`) keeps
`clickstream` (user decision). `clickstream_scd_modeling_sql` is not an
Auto Loader variant: it writes to `bronze_clickstream_publish` from the
canonical `web_events_raw`, so it keeps `clickstream` and stays exempt. The rename is display-name only:
resource keys stay (NAMING.md: never rename a deployed pipeline key), and
their tables stay in `bronze_clickstream`/`bronze_clickstream_publish`,
where their names already carry the variant (`web_events_rescue`,
`web_events_scd1_sql`, ...); moving them to a new schema would need the
iac repo and a table recreate for unused reference data. neon's reference
variants keep their names: the user's rename applied to clickstream only
(assumption, flagged for review).
Template display names: `bronze--template--autoloader--<language>--<mode>--<target>`.

## Risks / Trade-offs

- [The "Landing refresh fails" scenario relies on the engine skipping
  downstream datasets of a failed one] → standard pipeline behaviour, not
  re-proven here; it is the same guarantee the old wrapper job gave by task
  dependency.
- [Pending lists drift if a refactor forgets to edit them] → each refactor
  change lists "remove the source from the pending lists" as a task.
