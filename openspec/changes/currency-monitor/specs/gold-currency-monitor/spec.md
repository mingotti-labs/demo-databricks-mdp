## ADDED Requirements

### Requirement: Currency monitor signals
`gold_analytics_gateway.monitor_daily_signal` SHALL have, for monitor `currency`, on every `^GSPC` trading day: under
lens `us_dollar`, a `dollar_index` row (`is_yes` when the US Dollar Index `DX-Y.NYB` closes above its 200-day average)
and one row per main currency other than the US dollar (`is_yes` when its value in US dollars is above its 200-day
average); under lens `australian_dollar`, one row per main currency other than the Australian dollar, the US dollar
included (`is_yes` when its value in Australian dollars is above its 200-day average); and a `summary` row per lens with
`yes_count` the currencies gaining. A currency SHALL count on a day when its value is at most 10 days old. Each row SHALL
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
currency rows: the dollar megatrend (the index against its average), each main currency gaining or losing against the US
dollar and against the Australian dollar, and every country's short-term rate and 10-year yield with the date of the
reading and a mark when it is older than 3 months; and on a "Currency Deep Dive" page, for a chosen currency, its value in
US and Australian dollars with their averages and its rates over time.

#### Scenario: A stale rate
- **WHEN** Switzerland's latest short-term rate reading is from 2024-03
- **THEN** the rates table shows it with its date and the stale mark

### Requirement: Genie agent covers the currency monitor
The Genie agent SHALL state the currency rules in its instructions (value in a base, gaining above the 200-day average,
the cross-rate rule, the stale rates), take its examples for these questions from the Currency Monitor dashboard's queries,
and carry benchmark questions with SQL answers for them.

#### Scenario: Which currencies gain against the Australian dollar
- **WHEN** a user asks which currencies are gaining against the Australian dollar today
- **THEN** the agent lists the `australian_dollar` lens rows with `is_yes` true of the latest day
