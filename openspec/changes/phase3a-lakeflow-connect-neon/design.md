## Context

See proposal.md - Why. This is the roadmap's Phase 3, first ingestion pattern.
Reached via a full brainstorm covering: which Lakeflow Connect architecture pattern
is actually usable on Free Edition (query-based, confirmed by trying to create a
classic cluster and getting rejected — not assumed from docs), what domain and data
source to seed Neon with (synthetic e-commerce via Faker, not a real dataset — see
Decisions), and the Neon branching work that had to land first
(`phase1-neon-branching` in `iac`) so this pipeline has a `dev` branch to target
instead of the platform's single, undifferentiated data copy.

## Goals / Non-Goals

**Goals:**
- A real, working query-based ingestion pipeline from Neon into `bronze_neon`,
  verified end-to-end (seed → ingest → query the landed tables)
- Faker's use documented as an explicit architecture component, not left implicit
- Known limitations (delete-blindness) documented, not silently accepted

**Non-Goals:**
- CDC — that's roadmap Phase 3e, a separate, harder pattern with its own review
- Soft-delete tracking on the source — would make delete propagation work, but
  carries its own assumptions (the source app must never hard-delete, only flag)
  that aren't relevant to what this pattern needs to demonstrate; explicitly
  discussed and deferred, not an oversight
- `tst`/`prd` data — no separate Neon branch/instance backs them; pipeline code
  reaches those targets on promotion, real data does not

## Decisions

**Query-based Lakeflow Connect, not CDC-via-gateway.**
The gateway architecture pattern needs classic compute. Verified empirically that
Free Edition doesn't support it: `databricks clusters create` was rejected outright
with "Current organization ... does not have any associated worker environments" —
not a guess from documentation, a real API rejection. Query-based needs no gateway,
confirmed serverless-compatible.

**Synthetic (Faker) seed data, not a real dataset.**
Neon represents "the business's operational Postgres" for this platform — seeding
it should be fully controllable (volume, shape, referential integrity) and carry no
licensing/attribution burden, unlike loading a real dataset (e.g. the Olist
Brazilian E-commerce Kaggle dataset) would. Faker is used directly (no dedicated
"synthetic data" skill applies here — that tooling targets Spark+Delta output, not
an external Postgres instance).
Alternative considered: public "fake store" REST APIs (fakestoreapi.com,
dummyjson.com) — good candidates for a *different* pattern (API ingestion, roadmap
3c), not for seeding a database that's supposed to represent the source system
itself.

**E-commerce domain: customers, products, orders, order_items.**
Relatable, standard demo domain; sets up naturally for later roadmap phases (churn
/ demand-forecast ML, a RAG/GenAI use case over product data).

**Seeding via a Databricks job, not a local script.**
Uses the `neon-postgres` secret scope (originally provisioned in `phase1-core-
infrastructure`, re-wired to `dev` by `phase1-neon-branching`), runs on serverless
compute, reproducible via the bundle. First real consumer of that secret scope.

**No `deletion_condition` — delete-blindness accepted and documented, not hidden.**
Query-based ingestion without it silently misses hard deletes (a deleted source row
just stops appearing in query results — no event to observe). This was explicitly
discussed: soft-delete tracking would fix it, but requires the source application
to never hard-delete, only flag — a real assumption this demo doesn't need to make.
Documented here and in CLAUDE.md rather than silently glossed over.

**Cursor column: `updated_at` on every table.**
Required by query-based mode (`table_configuration.query_based_connector_config.
cursor_columns`) — the seed schema includes it on all four tables specifically so
the connector has what it needs.

**No default schedule.**
Matches `hello_world`'s pattern (manually triggered). A demo pipeline that's run on
demand is simpler to reason about than one silently accumulating scheduled runs
against synthetic data; add a Jobs `pipeline_task` + cron when there's a real reason
to automate it.

**Schema evolution: rely on Lakeflow Connect's built-in handling for columns,
explicit table list for tables — documented, not silently assumed.**
Checked against Databricks' own FAQ rather than the general (CDC-oriented) summary
in the skill's cached reference:
- **New column** on an already-ingested table: auto-ingested on the next run;
  historical rows get `NULL`. No action needed.
- **Removed column**: not dropped from `bronze_neon` — marked `inactive` and kept.
  If a same-named column later reappears, the pipeline *fails* until a full refresh
  or a manual drop of the inactive column. Worth knowing so that failure doesn't
  read as unrelated/mysterious if it happens.
- **New table** (e.g. a future `reviews` table in Neon): **not** auto-picked up.
  This pipeline lists each table explicitly (`objects: [{table: {source_table:
  customers}}, ...]`) rather than ingesting the whole schema — a deliberate v1
  choice (explicit and predictable over implicit and automatic), not an oversight.
  Adding a table means adding a `table:` block and redeploying.
- **Data type change** (e.g. `price` from `NUMERIC` to `DOUBLE`): not confirmed for
  query-based Postgres specifically in the docs reached. General Lakeflow Connect
  guidance says this "typically requires a full snapshot reload" — treated as
  expected-but-unverified, not stated as settled fact.

**A standing, re-runnable verification suite — not just one-off manual checks.**
Everything verified so far this project (the UC Connection's live query, the Neon
secret's resolved value, etc.) was a throwaway check: run once, discarded. That
proves the pattern worked *at implementation time*, not that it still works later.
This change introduces `verification/` — Databricks notebooks, one assertion focus
each, chained into a multi-task job (`verify_neon_ecommerce_pattern.job.yml`) so the
whole pattern can be re-checked with one `databricks bundle run` at any point in the
future: connection liveness, seed data integrity, and ingested-row-count parity.
Kept separate from `tests/` deliberately — `tests/common/` is pytest against
importable Python with no network/live-environment dependency; these notebooks are
the opposite (live environment, no local execution), and conflating the two would
misrepresent what either actually checks.
Alternative considered: fold these checks into the CI/CD pipeline (`main.yml`) as an
automated post-deploy step — not done here; that's a real future extension, but
scoping it now would pull in decisions (what should block a deploy vs. just warn,
how failures get surfaced) that belong to their own change once there's more than
one pattern's worth of verification suite to justify it.

## Risks / Trade-offs

- [Hard deletes in the source are invisible to this pipeline] → Mitigation:
  documented here, in proposal.md, and in CLAUDE.md; a deliberate, accepted
  limitation, not a gap to be "discovered" later.
- [Higher query load on Neon each run, vs. true CDC] → Mitigation: acceptable at
  this data volume (a few thousand synthetic rows); revisit if Neon's compute-hour
  quota becomes a real constraint.
- [Depends on `iac`'s `neon_dev` connection landing and being verified first] →
  Mitigation: explicit Cross-repo dependency in proposal.md; this change's own
  tasks.md re-checks connectivity before building on it, rather than assuming the
  other change's verification is still valid.
- [Removing then re-adding a same-named column on the source fails the pipeline,
  not just warns] → Mitigation: documented in this Decision and in CLAUDE.md, so a
  future failure here is recognized immediately instead of debugged from scratch.

## Migration Plan

1. Confirm `phase3a-neon-uc-connection` (iac) is applied and its connectivity
   verification passed.
2. Deploy + run the seed job — tables must exist with data before the ingestion
   pipeline has anything to query.
3. Deploy + run the ingestion pipeline.
4. Deploy + run the `verification/` suite (`verify_neon_ecommerce_pattern` job) —
   confirms connection liveness, seed data integrity, and ingested-row-count parity
   in one pass, and becomes the standing way to re-check this pattern going forward.

Rollback: `databricks bundle destroy --target dev` removes both new resources;
`TRUNCATE` (or nothing — Neon `dev` stays disposable by design) removes the seeded
data. Nothing else depends on this yet.
