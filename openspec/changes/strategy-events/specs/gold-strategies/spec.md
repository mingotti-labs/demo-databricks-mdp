## ADDED Requirements

### Requirement: Strategy events table
`gold_analytics_gateway.strategy_daily_event` SHALL have one row per `strategy_code`, `trading_symbol_code`,
`event_date` and `event_code`, only when an event happens: `setup_start`, `entry` or `setup_end`. Each row SHALL carry
`strategy_name`, `event_name`, `listing_id`, `setup_start_date` (the date of its setup period's `setup_start`), a plain
`reason_text`, `currency_code` and `ingested_timestamp`; an `entry` row SHALL also carry `entry_number` (1, 2, ... by date
within the setup period) and `is_first_entry` (true on number 1). Events SHALL be evaluated on complete Monday-based weeks
(the last trading day is a Friday, or that week's Friday has passed) whose last day has a market climate row, and the setup
SHALL count as on only when either climate lens is red on that day. Every column SHALL carry a Unity Catalog description.

#### Scenario: A setup period
- **WHEN** a strategy's setup is off in week 1, on in weeks 2 to 4 and off in week 5
- **THEN** the table has a `setup_start` on week 2's last day and a `setup_end` on week 5's last day, both with
  `setup_start_date` week 2's last day, and no row for weeks 1, 3 and 4 unless an entry fires

#### Scenario: A holiday Friday
- **WHEN** a week's last trading day is a Thursday because Friday is a holiday, and the run is after that Friday
- **THEN** the week is evaluated with Thursday's close as its week close

#### Scenario: The current week
- **WHEN** the latest price is on a Wednesday
- **THEN** that week is not evaluated as a week yet; only an interim entry (strategy 001) can be dated in it

### Requirement: Strategy 001 bear market fund
For `strategy_code` `bear_market_fund` on `^GSPC` (`price_close`), the setup SHALL be on in a week when the climate is red
and the week's close is below the close five weeks earlier. While the setup is on, an `entry` SHALL be written on the
week's last day when the week's change is at most -5% (`entry_band_code` `half_of_equity`) or at most -2.5%
(`quarter_of_equity`); when the change is below 0 and above -2.5%, on the first Monday, Tuesday or Wednesday of the next
week whose close is at least 2.5% below that week's close (`interim_quarter_of_equity`). Rows SHALL carry
`week_close_amount`, `five_weeks_close_amount` and `week_change_ratio`.

#### Scenario: A quarter entry
- **WHEN** the setup is on and the S&P 500 closes a week 3.1% below the previous week
- **THEN** an `entry` with `entry_band_code` `quarter_of_equity` is dated on that week's last day

#### Scenario: An interim entry
- **WHEN** the setup is on, a week closes 1% down, and the next Tuesday closes 2.6% below that week's close
- **THEN** an `entry` with `interim_quarter_of_equity` is dated on that Tuesday

### Requirement: Strategy 002 short selling
For `strategy_code` `short_selling`, on each current S&P 500 member of a week's last day, the setup SHALL be on when the
climate is red and the member's `price_to_sales_ratio` that day is above 15. While the setup is on, an `entry` SHALL be
written on the week its streak of weekly adjusted closes below the previous week's reaches six. A member absent from the
index on a week's last day SHALL count as setup off. Rows SHALL carry `price_to_sales_ratio` and `down_week_count`.

#### Scenario: Six weeks down
- **WHEN** a member's setup is on and its adjusted weekly close has fallen six weeks in a row
- **THEN** an `entry` is dated on the sixth week's last day, and a seventh week down writes no new entry

#### Scenario: No revenue
- **WHEN** a member's `price_to_sales_ratio` is empty
- **THEN** its setup is off
