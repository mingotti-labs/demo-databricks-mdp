## Context

See proposal.md - Why. This is the second ingestion pattern in this repo, after
`neon-ecommerce-ingestion` (Lakeflow Connect, query-based). The `databricks-
pipelines` skill's own decision tree routes file ingestion from cloud
storage/Volumes straight to Auto Loader inside a Streaming Table — there isn't a
real architectural choice to make here the way 3a had (query-based vs.
CDC-gateway); the design work is in the schema-evolution story and the
multi-environment seed generation, not the ingestion mechanism itself.

## Goals / Non-Goals

**Goals:**
- Land synthetic clickstream files into `bronze_clickstream.web_events_raw` via
  Auto Loader, with schema evolution genuinely exercised (not just configured)
- Each environment generates and ingests its own independent synthetic data
- A verification suite that re-proves the pattern on demand, matching 3a's
  standard

**Non-Goals:**
- Any transformation beyond raw landing (silver/gold modeling is Phase 4)
- A "processed" or archive folder for ingested files — not needed for
  correctness (see spec's "Files are not moved or deleted" requirement); if a
  real need shows up later, `cloudFiles.cleanSource.moveDestination` handles it
  without restructuring the landing path
- Promotion/copying of dev-generated data into tst/prd — each environment's
  data is independently synthetic, so there's nothing to promote

## Decisions

**`cloudFiles.schemaEvolutionMode = "addNewColumns"`, not `rescue` or
`failOnNewColumns`.**
`addNewColumns` (Auto Loader's own default) mirrors the story already
established for `neon-ecommerce-ingestion`'s Lakeflow Connect pipeline: a new
field just gets backfilled as `NULL` for rows that predate it, no pipeline
change required. Setting it explicitly rather than relying on the implicit
default keeps the choice visible in the pipeline source, per the proposal's own
point that this pattern exists to make schema evolution an explicit, inspectable
setting (unlike 3a's automatic connector behavior).

**`cloudFiles.schemaLocation` is not set.**
Per the `databricks-pipelines` skill's Auto Loader reference: inside a Lakeflow
Declarative Pipeline, the pipeline manages schema location and checkpoint
automatically — setting it manually is an anti-pattern the skill explicitly
warns against, not a judgment call for this design to make.

**Each environment generates independent synthetic data — no cross-environment
promotion.**
Diverges from how a real clickstream source would work (one upstream system,
promoted/replicated data), but is consistent with `neon-ecommerce-ingestion`'s
own seed-data being synthetic and per-branch — and per direct instruction, since
the data is synthetic anyway, there's no correctness reason to prefer promotion
over independent per-environment generation.

**Schema-evolution verification is a real generate-then-rerun test, not a
one-off manual check.**
Mirrors 3a's standing-verification-suite precedent: `verification/` notebooks
that can be re-run on demand, not just proven once at build time. The specific
test (spec's "New columns are ingested without a pipeline change" requirement)
generates a batch with a new field, reruns the pipeline, and asserts the new
column exists with `NULL` for older rows — the same shape of proof 3a used for
its own schema-evolution claims, but for Auto Loader's mechanism instead of
Lakeflow Connect's.

## Risks / Trade-offs

- [Whether the deployed pipeline/job's run-as identity (the CI/CD service
  principal) has sufficient access to read/write the `s3_clickstream_raw`
  volume is unverified — flagged as a risk in `phase3b-clickstream-volume`'s
  design.md, not resolved there] → Mitigation: this change's own apply/run is
  where that gets proven or disproven for real; if a permission error surfaces,
  add the specific grant it names in `demo-databricks-iac` as a fast-follow,
  same discovery path as `neon_dev`'s `USE_CONNECTION` grant.
- [Auto Loader's `addNewColumns` mode is documented to fail the current
  micro-batch once when a genuinely new column is first seen, before picking up
  the new schema on retry] → **Confirmed empirically** during implementation:
  the flow terminated with `"Flow ... has encountered a schema change during
  execution and terminated. A new update using the new schema will be
  automatically started."`, the pipeline update was `CANCELED` (cause
  `SCHEMA_CHANGE`), and Databricks itself started a new update (cause
  `SCHEMA_CHANGE`) which completed successfully — a clean, self-driving
  restart, not an error state a human or job retry policy needs to handle.
  The triggering `databricks bundle run` CLI call does exit non-zero
  (`Error: update cancelled`) even though the pipeline recovers on its own —
  worth knowing so a CI/CD job calling `bundle run` doesn't misreport this as
  a real failure.

## Migration Plan

Net-new. Depends on `phase3b-clickstream-volume` (see proposal.md's cross-repo
dependencies) landing first. Deploy to `dev`, verify via the
`verify_clickstream_pattern` job, then promote to `tst`/`prd` the same way
`neon_ecommerce_ingestion` was. Rollback: remove the job/pipeline resources from
the bundle and redeploy — no destructive state, since the pattern only ever
appends to `web_events_raw`.
