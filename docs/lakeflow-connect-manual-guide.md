# Lakeflow Connect: manual walkthrough (Neon → bronze_neon)

This mirrors, step by step through the Databricks UI, what `phase3a-neon-uc-connection`
(Terraform, in `demo-databricks-iac`) and `phase3a-lakeflow-connect-neon` (this repo's
bundle) do as code. Use it to check the automated result by hand, or to build a
throwaway copy of the pattern yourself to learn the UI flow — this is your first time
using Lakeflow Connect.

Everything here targets the Neon **`dev`** branch specifically, not `main`. Get its
connection string from the Neon Console (console.neon.tech → your project → branch
selector at the top → switch to `dev` → **Connect** button) before starting.

## 1. Create the UC Connection

1. In the Databricks workspace, open **Catalog Explorer** (left sidebar).
2. Go to **External Data → Connections**.
3. Click **Create connection**.
4. Choose **PostgreSQL** as the connection type.
5. Fill in:
   - **Host**: the `dev` branch's host from the Neon connection string (looks like
     `ep-<something>.<region>.aws.neon.tech` — **not** the `main` branch's host,
     they're different endpoints)
   - **Port**: `5432`
   - **User**: `app`
   - **Password**: the `dev` branch's password (from the same Neon connection string)
6. Name it something like `neon_dev_manual` (to avoid colliding with the Terraform-
   managed `neon_dev`).
7. Click **Create**. Databricks tests the connection at creation time — if the host/
   credentials are wrong, it tells you immediately.

> The Terraform-managed version of this step tried setting an `sslmode` option and
> was rejected outright by the API — this connection type doesn't support it. You
> won't see that option in the UI form at all, which is the same information the API
> error was telling us.

## 2. Verify the connection actually works

Unlike some Databricks objects, a bare Connection isn't independently browsable —
`SHOW SCHEMAS IN CONNECTION <name>` is not valid syntax (confirmed the hard way while
building the automated version). To actually check it:

1. In Catalog Explorer, click into your new connection.
2. Click **Create catalog** (this creates a *foreign catalog* on top of the
   connection — the standard way to browse/query through it).
3. Set the catalog name (e.g. `neon_dev_manual_catalog`) and database `app`.
4. Once created, expand it in Catalog Explorer — you should see schemas including
   `public`, `pg_catalog`, `information_schema`. Seeing `public` (with `customers`,
   `products`, `orders`, `order_items` inside it, once the seed job has run) is your
   proof the connection genuinely reaches Neon's `dev` branch.
5. You can delete this catalog afterward (right-click → Delete) — it's not needed
   for the actual ingestion pipeline, only for browsing/verification.

## 3. Create the ingestion pipeline

1. In the Databricks workspace, go to **Jobs & Pipelines** (left sidebar) → **Create**
   → **ETL Pipeline**.
2. Choose **Add data** → look for **PostgreSQL** under database connectors, or start
   from **Ingestion pipeline** and pick your connection (`neon_dev_manual` or the
   Terraform-managed `neon_dev`).
3. When prompted for the ingestion mode, pick the **query-based** option (not CDC) —
   this workspace doesn't have classic compute available for the CDC gateway, so CDC
   setup will fail here.
4. Select the tables to ingest: `customers`, `products`, `orders`, `order_items`
   (from the `app` database, `public` schema).
5. For each table, you'll be asked for a **cursor column** — use `updated_at` for
   all four (every seed table has one specifically for this).
6. Set the destination catalog/schema — `mdp_dev` / `bronze_neon` to land in the same
   place the automated pipeline does (or a different schema if you want to keep your
   manual copy separate).
7. Leave deletion tracking off — this pattern deliberately doesn't track deletes (see
   this change's `design.md` for why).
8. Save and run the pipeline. Watch the run's flow list — you should see one flow per
   table, each going through `QUEUED → STARTING → RUNNING → COMPLETED`.

## 4. Confirm the result

Query the destination tables and compare row counts against Neon directly (via the
foreign catalog from step 2, or the connection's own browsing) — they should match
exactly, the same check `phase3a-lakeflow-connect-neon`'s automated
`verification/verify_bronze_neon_ingestion.py` performs.

## What to expect if you add or remove columns/tables afterward

See this change's `design.md` "Schema evolution" decision — briefly:

- A **new column** on an already-ingested table shows up automatically on the next
  pipeline run; older rows get `NULL` for it.
- A **removed column** doesn't disappear from the destination — it's marked
  `inactive`. If you later re-add a column with the same name, the pipeline will
  **fail** until you do a full refresh or manually drop the inactive column.
- A **new table** in Neon is **not** picked up automatically — this pipeline lists
  tables explicitly rather than ingesting the whole schema, so you'd need to add it
  through the UI (or the equivalent `table:` block in code) and redeploy/rerun.
