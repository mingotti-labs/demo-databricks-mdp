# gold-currency-monitor Specification

## Purpose
TBD - created by archiving change currency-monitor. Update Purpose after archive.

## Requirements

### Requirement: Currency monitor signals
`gold_analytics_gateway.monitor_daily_signal` SHALL have, for monitor `currency`, on every `^GSPC` trading day: under
lens `us_dollar`, a `dollar_index` row (`is_yes` when the US Dollar Index `DX-Y.NYB` closes above its 200-day average), a
`dollar_broad_index` row (the same rule on the Federal Reserve's broad dollar index, as context)
and one row per main currency other than the US dollar (`is_yes` when its value in US dollars is above its 200-day
average); under lens `australian_dollar`, one row per main currency other than the Australian dollar, the US dollar
included (`is_yes` when its value in Australian dollars is above its 200-day average); and a `summary` row per lens with
`yes_count` the currencies gaining (the two index rows are not counted). A currency SHALL count on a day when its value is at most 10 days old. Each row SHALL
carry the value as `measured_value`, the average as `threshold_value`, a `band_code` (red at or below the average, green
above it with a rising average, else yellow) and a plain `reason_text`. The rows of the other monitors SHALL not change.

#### Scenario: The franc gains against the Australian dollar
- **WHEN** on a day the Swiss franc's value in Australian dollars is above its 200-day average
- **THEN** the `australian_dollar` lens has a `chf` row with `is_yes` true for that day

#### Scenario: Other monitors unchanged
- **WHEN** the change is deployed
- **THEN** the `market_climate` and `inflation_deflation` rows equal the rows before it

### Requirement: Currency Monitor dashboard
A dashboard "Currency Monitor" SHALL read the target's catalog and show, as of a date defaulting to the latest day with
currency rows: the dollar megatrend as two circles (the US Dollar Index and the broad index, each against its average), each main currency gaining or losing against the US
dollar and against the Australian dollar, and every country's short-term rate and 10-year yield with the date of the
reading and a mark when it is older than 4 months; and on a "Currency Deep Dive" page, for a chosen currency, its value in
US and Australian dollars with their averages, and its short-term rate and its 10-year yield over time (the 10-year when
the country has one).

#### Scenario: A stale rate
- **WHEN** the euro area's latest 10-year yield reading is from 2026-01
- **THEN** the rates table shows it with its date and the stale mark

#### Scenario: The 10-year on the deep dive
- **WHEN** the user picks the Swedish krona on the Currency Deep Dive page
- **THEN** its short-term rate and its 10-year yield are shown over time; for the yuan only the short-term rate

### Requirement: Yield Deep Dive
The Currency Monitor dashboard SHALL have a page "Yield Deep Dive" with a base currency selector (the Australian dollar by
default, the US dollar the other choice) and a table of the main currencies' countries ranked by the short-term interest
rate in percent plus the change of the currency's value in the base over the last 252 trading days in percent (none for
the base itself), showing for each the short-term rate and its reading date, the 10-year yield when it has one, the
currency change, the distance from its 200-day average and the sum. A country without a current short-term rate or
without a year of history SHALL not be ranked.

#### Scenario: Ranking in Australian dollars
- **WHEN** the base is the Australian dollar and the Australian short-term rate is 4.60 and every other currency has lost
  value against the Australian dollar over the year
- **THEN** the Australian dollar ranks first with a sum of 4.6 and the table shows the change of every other currency as
  negative

#### Scenario: Ranking in US dollars
- **WHEN** the user picks the US dollar as the base
- **THEN** the same table is shown with each currency's change against the US dollar and the US dollar with no change

### Requirement: Genie agent covers the currency monitor
The Genie agent SHALL state the currency rules in its instructions (value in a base, gaining above the 200-day average,
the cross-rate rule, the stale rates), take its examples for these questions (the Yield Deep Dive ranking included, so that a ranking is
always the short-term rate plus the 12-month currency change in percent, said to be backward-looking) from the Currency Monitor
dashboard's queries,
and carry benchmark questions with SQL answers for them.

#### Scenario: Which currencies gain against the Australian dollar
- **WHEN** a user asks which currencies are gaining against the Australian dollar today
- **THEN** the agent lists the `australian_dollar` lens rows with `is_yes` true of the latest day
