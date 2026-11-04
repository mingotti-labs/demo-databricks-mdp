## Context

Change 3 (`market-climate-gold`) built `index_valuation_daily` and `monitor_signal_daily` in
`gold_analytics_gateway`. The per-member step (CTEs `members` .. `valued` in
`src/common/market_climate_sql.py`) is computed and thrown away; only day totals are kept. The user wants to
go from the light down to the numbers: first to check them, then, once trusted, to explain them.

## Goals / Non-Goals

**Goals:** every figure behind a light traceable to member rows; one place the per-member logic lives; a
dashboard that checks and explains the climate; queries tested by CLI and reusable by the Genie agent.

**Non-Goals:** the Genie agent (change 5); a semantic layer (metric views; separate planning); a sector
table; index membership history.

## Decisions

### D1. Names (user, 2026-11-05)
Gold tables: subject, then grain, then detail. `valuation_daily_index`, `valuation_daily_index_member`,
`monitor_daily_signal` (the monitor comes first: it is what a reader looks for). NAMING.md "Gold tables"
states the rule with these three examples. Column names keep the Silver Domain endings.

### D2. `valuation_daily_index_member`: one row per `index_code`, `valuation_date`, `company_id`
Every current member (one listing per company, as today) on every valuation day, used or not. Columns:
- keys and trace: `index_code`, `valuation_date`, `company_id`, `listing_id`, `price_date` (date of the
  close used), `filing_valid_from_date` (the `company_fundamentals` row valid that day)
- inputs: `price_close`, `share_count`, `share_count_source_code` (`cover_page` / `weighted_average`),
  `earnings_trailing_twelve_months_amount` (the filing's `net_income`), `earnings_ten_year_average_amount`,
  `earnings_year_count`, `filing_consumer_price_index_value` (the filing row's CPI),
  `consumer_price_index_value` (that day's CPI)
- derived: `earnings_ten_year_average_inflation_adjusted_amount` (stored average x day CPI / filing CPI, in
  that day's money), `market_value_amount` (close x shares)
- use: `is_used`; `exclusion_reason_code`, the first failing of `no_recent_price`, `no_filing`,
  `no_share_count`, `no_net_income`, `no_ten_year_average`, `no_consumer_price_index` (empty when used)
- position, used members only, on the 10-year inflation-adjusted ratio (the one that votes):
  `market_value_share_ratio` (member market value / index market value),
  `price_earnings_ten_year_average_inflation_adjusted_ratio` (the member's own; empty when its earnings are
  not positive), `price_earnings_without_member_ratio` (index market value minus the member's / index
  earnings minus the member's; empty when that earnings total is not positive),
  `price_earnings_effect_ratio` (index ratio minus the "without" ratio: positive pushes the P/E up)
- `currency_code`, `ingested_timestamp` (earliest of its price and filing rows)

The index totals the "without" figures need are window sums over the used rows of the same day, inside
this table's query. Effects do not add up to the index P/E; the dashboard shows them next to it.

### D3. `valuation_daily_index` from the member rows
`common/market_climate_sql.py` splits into `index_member_valuation_query()` (the member step, D2) and
`index_valuation_query(member_source)` (group by day). Same columns and values as `index_valuation_daily`;
`members_without_shares_count` keeps its meaning (a price but no share count: reasons `no_filing` and
`no_share_count`). Member amounts are not rounded before summing, so totals match to the cent.
`monitor_daily_signal` keeps `monitor_signal_query`, reading `valuation_daily_index`.

### D4. Switch-over and drops (approved by the user, 2026-11-05)
A dataset removed from a pipeline keeps its table (probe P1 of the pipeline-per-layer work), so after the
deploy the old and new tables exist side by side. Per environment: run, compare old and new day by day
(probe P1 below; `EXCEPT` both ways on every column but `ingested_timestamp`, plus the timestamps), then
drop `index_valuation_daily`, `monitor_signal_daily` and their `__materialization_mat_*` twins with
`references/poc/table-cleanup/drop_tables.py`, literal names. Dev before the implementation PR is ready;
prd after its deploy. A difference stops the drop and is explained first.

### D5. Dashboard
`resources/dashboards/market_climate.dashboard.yml`, JSON `src/dashboards/market_climate.lvdash.json`,
`dataset_catalog: ${var.catalog}`, `dataset_schema: gold_analytics_gateway`, warehouse looked up by name
(Serverless Starter Warehouse). Queries name tables without the catalog so each target reads its own.
Every dataset query is run by CLI first (skill rule) and saved under `references/poc/market-climate-dashboard/`.
- **Date**: each page has a date parameter defaulting to the latest day with a climate row; tile "Climate
  as of <date>". Freshness tiles: latest `^GSPC` price, latest Fed target reading, latest CPI month (silver).
- **Climate**: two lights (counter or table per lens) with the three answers, measured value, line and
  `reason_text`; light history (both lenses, colour by band); P/E chart (10-year inflation-adjusted and
  trailing, lines 16, 22, 30); Fed target with change days and their 6-month windows; `^GSPC` with its
  200-day average.
- **Climate Deep Dive**: index row of the day (market value, earnings, ratio, members used of all);
  top 10 by `price_earnings_effect_ratio` (pushes up), bottom 10 (pushes down), each with "P/E without it";
  excluded members with their reason; all members (sector, used filters); checks: member sums minus index
  row (expected 0), and one company picked from a list worked through (close x shares; average x CPI ratio).
- **Sector Deep Dive**: sector parameter; sector P/E (sector market value / sector earnings) against the
  index P/E; index P/E without the sector; the sector's top and bottom members by effect; one row per
  sector for the day. Sector is `company.gics_sector_name`, today's sector (said on the page).
- Permissions: the user can open the dev and prd copies (checked; add bundle permissions if not).

### D6. Descriptions
Every column of the member table carries a description written for the Genie agent (formula, units,
window, which ratio, sign of the effect). The renamed tables keep theirs; table comments name their sources.

## Risks / Trade-offs

- [A date parameter cannot default to "latest" in the dashboard JSON] -> the queries use the parameter
  when set and the latest day otherwise; probe P2 confirms before building pages.
- [The member table is about 500 x 256 rows and grows by 500 a day] -> small; a full refresh per run as now.
- [prd peaks at 488 slots during the switch, the stop line] -> the drop follows straight after the compare.
- [Sector is today's for every day] -> same as membership; on the page and in descriptions.

## Migration Plan

Draft PR deploy-dev -> run `investments` -> P1 compare -> drop old dev tables -> ready, merge -> CI runs
`investments` in prd -> P1 compare in prd -> drop old prd tables -> archive.
Rollback: revert; the old tables are gone after the drop, so a revert rebuilds them on the next run.

## Probes

- P1: old and new tables equal, per environment (dev, prd).
- P2: dashboard date parameter defaulting to the latest day.
- P3: each dataset query by CLI, results saved.
- P4: the SP-deployed dashboard opens for the user in dev.

## Open Questions

None.
