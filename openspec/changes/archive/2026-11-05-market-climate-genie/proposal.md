## Why

Change 5 of 5 of the market climate story (planning `docs/superpowers/specs/2026-11-04-market-climate-story-design.md`;
rules, definitions and the worked example in `references/user-stories/monitor-understand-market-climate.md`).
The dashboard answers the questions it was built for; a person who wants to ask something else ("which
sector lifts the P/E most?", "when did the modern light last turn yellow?", "why is EQT's P/E so high?")
has to write SQL. A Genie agent over the same gold tables answers in plain language, with the story's
rules as its instructions and the dashboard's tested queries as its worked examples, so its answers agree
with the dashboard.

## What Changes

- **Genie agent "Market Climate"** as a bundle resource (`resources/genie/market_climate.genie.yml`,
  `genie_spaces`), deployed by CI like the dashboard, in dev and prd, on the Serverless Starter Warehouse
  (`var.warehouse_id`). Viewers: the `users` group can run it.
- **Data**: `gold_analytics_gateway.valuation_daily_index`, `valuation_daily_index_member`,
  `monitor_daily_signal`, and `silver_domain_investments.company` (name and sector) and `price_daily`
  (prices for company questions), each named with the target's catalog. Join specs say how they relate
  (member to company by `company_id`, member to index by `index_code` and `valuation_date`, member to price
  by `listing_id`).
- **Instructions** from the story: the three questions and their thresholds (P/E above 22 long run, 30
  modern; a hike in the last 6 months; the S&P 500 above its 200-day average), yes as the unfavourable
  answer, the lights (red 2-3 yes = sell, yellow 1 = buy and hold, green 0 = strong buy), the three P/E
  measures and which one votes, what the effect on the index P/E means, why a member is left out, and the
  worked example. The table and column descriptions already in Unity Catalog carry the rest.
- **Example SQL**: the dashboard's dataset queries, rewritten for Genie (fully named tables, "latest day"
  instead of the date parameter), each paired with the question it answers. One file of queries feeds both
  the dashboard and the agent, so a change to a query changes both.
- **Sample questions** shown in the agent's UI, and **benchmark questions** with their SQL answers, run
  in dev through Genie's evaluation to check the agent picks the right numbers.
- **Generated, not hand-written**: a builder writes the agent resource from the shared queries and an
  instructions file, as the dashboard builder writes the dashboard JSON. The queries and both builders move
  from `references/poc/market-climate-dashboard/` into the repo's own code, with a test that the
  committed files equal the builders' output.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `gold-market-climate`: adds the Genie agent (its example SQL is the dashboard's queries, so both give the same figures).

## Impact

- Table slots: none (a Genie agent is not a table). Quota stays at 482/500.
- New bundle resource type `genie_spaces` (CLI 1.16.1 has it: title, warehouse_id, parent_path,
  permissions, `serialized_space` inline or `file_path`). Genie works on this Free Edition workspace (the
  starter space runs on the same warehouse). Not yet known: that the CI service principal can create one,
  and that `${var.catalog}` resolves inside `serialized_space` (it has no `dataset_catalog`, so table names
  must carry the catalog). Both are probed first (design P1).
- Moved files: `references/poc/market-climate-dashboard/{queries,build_dashboard}.py` to `src/`; the
  dashboard JSON is regenerated and must not change.
- Runs: no pipeline or job changes; the deploy creates the agent. No unit runs because of it.
- Not in this change: tags (an environment tag on every object, dashboards and the agent included, is its own
  change: the bundle tags jobs and pipelines but has no tag field for dashboards or Genie agents); a semantic layer (metric views, separate planning later); agent mode; Genie on the
  dashboard page ("Ask Genie" link) unless P1 shows it is a single field.

## Cross-repo dependencies

Depends on an iac change (found in P1): the CI service principal needs the `databricks-sql-access` entitlement so
the bundle can read a Genie agent back on the second deploy (see design.md, P1 result). Direction: this change's
deploy needs it; nothing in iac needs this change.

Earlier text, kept for the record: None. The CI/CD principal already reads `gold_analytics_gateway` and `silver_domain_investments`, and the
`users` group can use the warehouse. If P1 shows the principal needs a grant or entitlement to create a
Genie agent, that becomes an iac change first and this proposal is updated.
Planning repo: the story design marks change 5 done after archive.

## Model

Sonnet for implementation: the agent's content is settled here and the builder follows the dashboard's
pattern; switch to Opus if P1 shows the bundle resource or the principal cannot deploy the agent.
