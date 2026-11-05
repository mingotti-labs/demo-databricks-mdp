## Context

The dashboard "Market Climate" (change 4) runs 22 dataset queries, tested against dev, kept in
`references/poc/market-climate-dashboard/queries.py`. `build_dashboard.py` next to them writes
`src/dashboards/market_climate.lvdash.json`, which the bundle deploys with `dataset_catalog: ${var.catalog}`,
so its queries name tables without a catalog. Every gold column and table has a Unity Catalog description
written for a Genie agent. CLI 1.16.1 has the bundle resource `genie_spaces` (title, description,
warehouse_id, parent_path, permissions, `serialized_space` inline or `file_path` to a `.geniespace.json`).
It has no `dataset_catalog`: a Genie agent's tables and SQL name the catalog. Genie runs on this Free
Edition workspace (the "Bakehouse Sales Starter Space" uses the Serverless Starter Warehouse,
`c36e1ff0d4e62a24`). The CI service principal has no `databricks-sql-access` entitlement but deploys the
dashboard and owns it.

## Goals / Non-Goals

**Goals:** one agent per target, deployed by CI as code; the agent and the dashboard agree because they
share their queries; a check, before the PR is ready, that the agent answers the benchmark questions with
the right numbers.

**Non-Goals:** metric views or any semantic layer; agent mode; answering questions outside the market
climate story (other monitors add their own tables and examples later); a Genie link on the dashboard
(Open Questions).

## Decisions

### D1. Bundle resource with the catalog filled in by the bundle
`resources/genie/market_climate.genie.yml`, key `market_climate` under `genie_spaces`:
title "Market Climate", a one-line description, `warehouse_id: ${var.warehouse_id}`, permissions
`users` `CAN_RUN`, and `serialized_space` inline as YAML, where every table name is
`${var.catalog}.<schema>.<table>`. The bundle replaces `${var.catalog}` per target, so one file serves dev
and prd. Alternative: `file_path` to a JSON file, which the bundle inlines as it is (no variables), so it
would need one file per target and a target override for each; used only if P1 shows variables are not
replaced inside `serialized_space`.

### D2. One source for the queries
`queries.py` moves to `src/common/market_climate_queries.py` (unchanged content). `build_dashboard.py`
becomes `src/common/market_climate_dashboard.py` and a new `src/common/market_climate_genie.py` builds the
agent; each has a `build()` that returns the file content. `cicd/build_market_climate.py` writes both
files, and with `--check` fails when a committed file differs from its builder (as `apply_edition.py
--check` does). A pytest calls both `build()`s and compares them with the committed files. The regenerated
dashboard JSON must equal the deployed one byte for byte (the move changes nothing).

### D3. Example SQL from the dashboard queries
Each example pairs a question with one dataset query, changed for Genie by one function:
bare gold table names and `silver_domain_investments.` names get the `${var.catalog}` prefix;
`coalesce(:as_of_date, DATE '9999-12-31')` becomes `current_date()` (the latest day); `:sector_name`,
`:company_name` and `:range_code` become example values ('Information Technology', 'EQT Corporation',
'6M'), with `usage_guidance` saying which literal to replace. Questions:

| Question | Dataset |
|---|---|
| What is the market climate today? | ds_lights |
| What are the three answers of each climate today, and why? | ds_answers |
| How have the lights changed over time? | ds_light_history |
| What is the S&P 500 P/E today, on 10-year inflation-adjusted and on trailing earnings? | ds_index_day |
| How has the S&P 500 P/E moved over time? | ds_pe_history |
| Which companies push the index P/E up most? / down most? | ds_top_up, ds_top_down |
| Which members are left out today, and why? | ds_excluded |
| Do the member rows add up to the index? | ds_checks |
| What is the P/E of each sector, and the index P/E without it? | ds_sectors |
| How is EQT's P/E worked out, step by step? | ds_company_check |
| What are EQT's last close and 52-week high and low? | ds_company_figures |
| How fresh is the data? | ds_freshness |

Example ids are the first 32 hex characters of the MD5 of the dataset name, so regenerating does not change
them; lists are sorted by id as the API requires.

### D4. Instructions
`src/common/market_climate_genie_instructions.md`, one paragraph per rule, read by the builder into the single
allowed text instruction. Content, from the story's Analysis sections: the two climates and three
questions with thresholds per climate; yes is the unfavourable answer; lights and actions; the three P/E
measures (10-year inflation-adjusted votes, trailing and plain 10-year stored for comparison, with the
EQT example of why they differ); the effect on the index P/E (index P/E minus the P/E without the member,
one at a time, not additive); exclusion reasons; "today" means the latest `signal_date` / `valuation_date`;
the sector comes from `company.gics_sector_name`; dates are trading days; amounts are US dollars.

### D5. Data and joins
Tables (identifiers sorted, as the API requires): `company`, `price_daily`, `valuation_daily_index`,
`valuation_daily_index_member`, `monitor_daily_signal`. Join specs: member to company on `company_id`
(many to one), member to index on `index_code` and `valuation_date` (many to one), member to price on
`listing_id` (one to many, the price table filtered by date). Column configs: entity matching on
`company.company_name`, `company.gics_sector_name`, `monitor_daily_signal.lens_name` and `signal_name`
(small, stable sets a user names).

### D6. Benchmarks
Six benchmark questions with SQL answers taken from the examples but asked differently ("Is the market
too expensive right now?", "Which sector has the highest P/E?", "Why is EQT's P/E so high?", "Is the Fed
in the way?", "How many members are left out today?", "What did the long-run light say on 2026-10-01?"),
so the check is not the examples repeating themselves. Run with Genie's evaluation (`genie-create-eval-run`)
in dev (P3).

## Probes

- **P1** (first, before any builder work): a minimal `genie_spaces` resource (one table, one instruction)
  on the branch; the PR's `deploy-dev` deploys it as the CI principal. Pass: it deploys, and `genie
  get-space --include-serialized-space` shows `mdp_dev.` in the table name. If the principal cannot create
  it, stop and propose the grant or entitlement in iac.
- **P2**: every example SQL, as generated, runs on the warehouse in dev (the dashboard probe P3 pattern).
- **P3**: the benchmark evaluation in dev; every question passes, or the miss is explained and an
  instruction or example fixed. The evaluation needs edit rights on the agent: if `CAN_RUN` is not enough
  for the user, the dev target gives `users` `CAN_MANAGE` on it (dev only).
- **P4**: the user asks the spec's three scenarios in the dev agent and confirms; after merge, the same in prd.

## P1 result (2026-11-05)

Creating the agent as the CI principal works and `${var.catalog}` is filled in. Every later deploy fails while
planning: the bundle reads the agent back and gets 403 "You need the aclPath entitlement: /sqlanalytics",
because the principal has only `workspace-access`. It needs the `databricks-sql-access` entitlement
(`databricks_sql_access = true` on `databricks_service_principal.cicd_github` in iac
`modules/databricks-identity-governance`). This is the cross-repo dependency the proposal anticipated; the
entitlement also lets the bundle look a warehouse up by name again. Until it is granted, this PR's
`deploy-dev` fails.

## Risks / Trade-offs

- [Variables not replaced inside `serialized_space`] → one JSON file per target with a target override
  (D1 alternative), decided by P1.
- [The principal cannot create a Genie agent] → iac change first (grant or entitlement); the proposal says so.
- [Genie answers with a different P/E than the dashboard] → the examples are the dashboard's queries and
  the benchmarks check the numbers; misses fix an instruction or example, not the data.
- [Example SQL limited to literal values, not parameters] → `usage_guidance` names the literal to replace;
  parameterised examples can come later if needed.
- [A user edits the agent in the UI] → the next deploy overwrites it (dev deploy uses `--force`; prd edits
  would fail the prd deploy, as for the dashboard). Changes go through code.

## Migration Plan

Deploy creates the agent in dev (PR) and prd (merge). Rollback: remove the resource; the bundle deletes the
agent. No tables, so no drops and no quota change.

## Open Questions

- Whether the dashboard can link to the agent ("Ask Genie") with a single field; if it is one field, add it,
  otherwise leave it for later.
