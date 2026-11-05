## ADDED Requirements

### Requirement: Inflation deflation signals
`gold_analytics_gateway.monitor_daily_signal` SHALL have, for monitor `inflation_deflation` and lens `game_plan`,
on every `^GSPC` trading day where all four inputs have a row at most 7 days old, four star rows and one rating
row. A star is on (`is_yes` true) when: `commodity_prices`, the `^TRCCRB` 200-day average slope ratio is above 0;
`consumer_prices`, the 200-day average of the CPI index is higher than 20 rows earlier;
`gold_prices`, the `GC=F` adjusted close is above its 200-day average; `interest_rates`, the federal funds
effective rate is above its 200-day average. The `rating` row SHALL carry `yes_count` (stars on, 0 to 4),
`measured_value` (the rating: the stars on, or -1 when no star is on and the CPI 12-month change is below 0),
`threshold_value` (the CPI 12-month change), `action_name` (4 Increasing Inflation, 3 Inflation Danger, 2 Some
Inflation Risk, 1 Mild or Decreasing Inflation, 0 Decreasing Inflation, -1 Deflation), `band_code` and a
`reason_text`. Every row SHALL carry what was measured and what it was compared with. The market climate rows
SHALL not change.

#### Scenario: Deflation
- **WHEN** on a day no star is on and US CPI is below its level of 12 months earlier
- **THEN** that day's rating row has `measured_value` -1 and `action_name` Deflation

#### Scenario: No star but prices still rising
- **WHEN** on a day no star is on and the CPI 12-month change is 1.5
- **THEN** the rating is 0, Decreasing Inflation

#### Scenario: Market climate unchanged
- **WHEN** the change is deployed
- **THEN** the `market_climate` rows of `monitor_daily_signal` equal the rows before it

### Requirement: Inflation-Deflation Monitor dashboard
A dashboard "Inflation-Deflation Monitor" SHALL read the target's catalog and show, as of a date defaulting to the latest
day with a rating: the rating and its label with the four stars, the rating's history, one chart per star with
the line it is compared with, the real interest rate over time, the answers with their reasons and the date of
each input; and on a second page the eight commodity benchmarks against their 200-day averages.

#### Scenario: Reading the rating
- **WHEN** the user opens the dashboard
- **THEN** the rating shown equals the latest `rating` row of `monitor_daily_signal`

### Requirement: Genie agent covers the inflation monitor
The Genie agent SHALL also read `market_rate_indicator_daily` and `price_indicator_daily`, state the four stars,
the rating and its labels, the short-term rate and the real rate in its instructions, take its examples for these
questions from the Inflation-Deflation Monitor dashboard's queries, and carry benchmark questions with SQL answers for them.

#### Scenario: Real rate
- **WHEN** a user asks the agent for today's real interest rate
- **THEN** it answers with the latest `us_real_federal_funds_rate` and the two figures it is made of
