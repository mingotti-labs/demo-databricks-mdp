## Context

See proposal.md - Why. This extends `clickstream-autoloader-ingestion`'s
existing `addNewColumns` demonstration to the other three
`schemaEvolutionMode` values, in both Python and SQL — explicitly for
interview-prep/reference purposes, per direct instruction.

## Goals / Non-Goals

**Goals:**
- All 8 combinations (4 modes × 2 languages) exist as real, independently
  deployable pipeline resources — runnable on demand later, not just
  described in prose
- Each documents its own behavior and error/recovery workflow in-code
- The existing canonical pipeline's real data (400 rows, the confirmed
  schema-evolution proof) survives this reorganization intact

**Non-Goals:**
- Running the 3 additional Python modes or any SQL variant — per direct
  instruction, only `addNewColumns` (Python) needed re-proving; the other 7
  are built and validated, not executed
- A shared target table across variants of the same mode in different
  languages — each variant gets its own table, avoiding any pipeline
  ownership ambiguity (see Decisions)

## Decisions

**Move the canonical pipeline's source into its own folder; do not touch its
resource key.**
Multiple pipelines' source files need to live somewhere, and a shared
directory with a wildcard `libraries` glob would mean every pipeline picks up
every sibling's source file — causing duplicate/conflicting table
declarations across pipelines that were never meant to share a dataflow
graph. Isolating each variant into its own folder (`python_add_new_columns/`,
`python_rescue/`, etc.) avoids this entirely. The resource key
(`clickstream_autoloader`) is untouched — only the `libraries` glob path and
`name:` changed — confirmed via `bundle deploy` showing "Updated" for it, not
"Created", and the underlying table's 400 rows intact afterward. Renaming the
resource key itself was ruled out categorically after this project's own
incident earlier today (see `demo-databricks-iac`'s CLAUDE.md): that turns an
update into a destroy-then-recreate, which drops a pipeline's managed tables
by default.

**One target table per variant, never shared.**
Eight pipelines all writing the same table name would mean whichever one
runs first claims ownership, and the others would likely fail outright or
silently misbehave when Unity Catalog treats the table as already
pipeline-managed by someone else. Distinct table names per variant
(`web_events_raw`, `web_events_rescue`, `web_events_none_sql`, etc.) sidesteps
this — a real risk this project already has direct evidence for (the earlier
concern about the human-owned and CI/CD-SP-owned `neon_ecommerce_ingestion`
pipelines both targeting the same table name).

**`inferColumnTypes => false` set explicitly in every SQL variant.**
`read_files()` defaults `inferColumnTypes` to `true`; `cloudFiles` in Python
defaults it to `false` (all-string). Left at each language's own default,
the Python and SQL versions of the same mode would produce genuinely
different output schemas, making a side-by-side comparison misleading rather
than illustrative. Setting it explicitly and identically in every SQL
variant keeps the two languages' output comparable.

**`rescue`/`failOnNewColumns`/`none` documented from official docs, not
independently re-run.**
Per direct instruction: empirically re-verifying all four modes would cost
real time and Free Edition serverless quota (already hit once earlier
today), for marginal benefit over Databricks' own documented behavior. Only
`addNewColumns` — the one already run for real — carries a "confirmed live"
claim; the other three's source headers say plainly they're from
documentation, not verified here.

## Risks / Trade-offs

- [Eight pipelines is meaningfully more bundle/CI surface (validation time,
  resource count) than one] → Mitigation: acceptable for this project's
  explicit interview-prep goal; none of the 7 non-canonical pipelines are
  wired into `verify_clickstream_pattern` or any other automated check, so
  they add deploy-time cost only, not ongoing run cost.
- [Documentation for 3 of the 4 modes rests on Databricks' docs rather than
  this project's own verification] → Mitigation: explicitly labeled as such
  in every affected file's header, so a future reader (or the person
  studying from this code) knows exactly which claims are first-hand and
  which aren't.

## Migration Plan

Additive only — no destructive changes to `bronze_neon` or the existing
`web_events_raw` table. Deploy, confirm the canonical pipeline's data and
`pipeline_id` are unchanged, confirm all 7 new pipelines validate and deploy
successfully. Rollback: remove the 7 new resources and their source folders;
the canonical pipeline is untouched either way.
