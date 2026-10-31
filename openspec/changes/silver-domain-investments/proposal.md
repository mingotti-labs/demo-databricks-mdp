## Why

Step 9 of the dividend portfolio story (`demo-databricks-planning`) needs one
place where the six sources meet: today each source sits alone in
`silver_landing`, all values text, SEC figures under many concept names, and
nothing joins a ticker to its company, its prices, its dividends and its
fundamentals. Gold company metrics, the shortlist, the dashboard and Genie all
read from that place, so it comes first.

The user also asked (2026-10-31) for Net Current Asset Value (NCAV, NCAV per
share) and Graham's Number. Their inputs are SEC balance sheet figures we do not
keep yet (current assets, total liabilities, stockholders' equity, preferred
stock, EPS), so this change adds them to the concept mapping and carries them
in the fundamentals. The user also decided that Silver Domain schemas are named
`silver_domain_<domain>`, so the story's `silver_investments` becomes
`silver_domain_investments`.

## What Changes

- **Naming**: Silver Domain schemas are `silver_domain_<domain>` (NAMING.md,
  `references/docs/medallion/silver.md`); Silver Domain tables are named for
  what a row is, with a grain suffix when a row is one entity per period
  (`price_daily`). Names are spelled out, with no abbreviations (user,
  2026-10-31): `trading_symbol_code`, `central_index_key`,
  `earnings_per_share`; any cryptic name that stays is translated in gold.
  Entity ids (`company_id`, `listing_id`) are SHA-256 hashes of the source
  registry and number (64 hex characters), opaque and stable across rebuilds.
- **Concept mapping** (`data/portfolio/concept_mapping.csv`): new figures
  `current_assets`, `total_liabilities`, `liabilities_and_equity`,
  `stockholders_equity`, `total_equity`, `preferred_stock` and
  `earnings_per_share`. The SEC
  fetch already keeps every mapped concept and rewrites a company's file when
  its mapped facts change, so the next `run_sec` picks them up with no code
  change.
- **New pipeline** `silver_domain_investments` (`silver--domain--investments--<target>`),
  materialized views in `silver_domain_investments` read only `silver_landing`:
  - `company`: one row per company (hashed `company_id` from the SEC central
    index key), share classes linked, sector. No index columns: a company can
    be in many indexes.
  - `market`: one row per ISO 10383 operating market (`market_identifier_code`),
    from the new `iso-mic` Landing table.
  - `listing`: one trading symbol on one market (hashed `listing_id`), with
    `currency_code` and the `company_id` (empty for an index benchmark). There
    is no `security` or `financial_instrument` table yet (user, 2026-10-31);
    the trading symbol code sits on the listing until they exist.
  - `index_membership`: the S&P 500 membership history per listing, from the
    Wikipedia SCD2 versions.
  - `price_daily`: daily close and volume per listing, members and benchmarks,
    typed, with `currency_code`.
  - `dividend`: one row per listing and ex-date, with amount, `currency_code`,
    the AUD amount at the RBA rate, the pay date (real from the Yahoo calendar
    or estimated from the settings offset) and a special-dividend flag.
  - `company_fundamentals`: one row per company and reported date (the
    filing date of each 10-K or 10-Q, `valid_from_date`, the business key with
    the company), valid until the day before the company's next filing
    (`valid_to_date`, or 9999-12-31 for the latest). One column per mapped
    figure plus free cash flow, total debt and EBITDA, with the concept used
    for each figure: balance sheet figures at the filing's period end, income
    and cash flow figures as the trailing twelve months (user, 2026-10-31).
  - `market_rate_daily`: AUD/USD, the RBA cash rate target, the US 10-year yield and
    the three Fed funds series, one long table.
  - `options_activity`: the latest options flag and activity per listing.
- **Yahoo fetch**: `src/common/yahoo_market.py` adds `exchange_code` (Yahoo's
  exchange code) to the calendar row written for every symbol, so a listing's
  market comes with no new table (probe P2: Yahoo and SEC agree on all 503
  current members). The Silver Domain maps the code to the operating market.
- **New unit** `run_investments`: the pipeline, then (with `verify=true`) a
  domain verification notebook.
- **Not in this change**: NCAV, NCAV per share, Graham's Number and every other
  metric (gold, next change); scheduling; the world indexes (their own change).

## Capabilities

### New Capabilities
- `silver-domain-investments`: the first Silver Domain, conformed tables that
  join the dividend story's sources, with the concept mapping applied.

### Modified Capabilities
None. The SEC spec already keeps whatever the mapping lists; adding mapping
rows changes data, not requirements.

## Impact

- New: `src/layers/silver/domain/investments/`, `src/common/` helpers with unit
  tests where logic is testable offline (concept choice, special-dividend
  rule), `resources/pipelines/silver_domain_investments.pipeline.yml`,
  `resources/jobs/run_investments.job.yml`,
  `verification/verify_silver_domain_investments.py`.
- Changed: `src/common/yahoo_market.py` (calendar rows gain `exchange_code`;
  CI runs `run_yahoo`), `data/portfolio/concept_mapping.csv` (merging it runs
  `run_portfolio` in prd; the next `run_sec` rewrites every company's facts file
  once, about 500 files), NAMING.md, silver.md, CLAUDE.md, registers.
- Table quota: 9 materialized views, 2 slots each, in dev and prd: 36 slots.
  The count was 446 of 500 on 2026-10-31, so about 482 after, plus the
  `iso-mic` source (about 12). Together they pass the 488 stop line, so a
  table clean-up change comes before the second of the two deploys, and the gold
  change after this one does not fit without it.
- Schema quota: unchanged (one schema replaces another).

## Cross-repo dependencies

Depends on a new change in `demo-databricks-iac`, `silver-domain-investments-schema`:
it creates `silver_domain_investments` with the grants `silver_investments` has
and drops the empty `silver_investments`, in both deployments. It must be
applied before this change deploys to dev.

Depends on the `iso-mic` change in this repo (to be proposed): it ingests the
ISO 10383 market identifier code list into `silver_landing`, which `market`
reads. `iso-mic` is implemented first. It needs no iac change (the `iso` source
exists).

## Model

Opus for the proposal and design (first Silver Domain, it sets the convention);
Sonnet for the implementation once the design is agreed.
