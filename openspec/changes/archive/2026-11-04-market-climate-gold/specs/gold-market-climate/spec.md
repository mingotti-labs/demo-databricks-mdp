## ADDED Requirements

### Requirement: Index valuation per day
`gold_analytics_gateway.index_valuation_daily` SHALL have one row per `index_code` (`SP500`) and
`valuation_date`, for each `^GSPC` price date from the first date a current member has a price. The day's
used members SHALL be the current index members, one listing per company (the most traded over its last
60 price rows), that have a close on or up to 5 days before the date and a `company_fundamentals` row
valid on the date with a share count (cover-page, else weighted average basic), `net_income` and both
10-year averages. Over the used members the row SHALL carry `market_value_amount` (close x shares),
`earnings_trailing_twelve_months_amount` (sum of `net_income`), `earnings_ten_year_average_amount`,
`earnings_ten_year_average_inflation_adjusted_amount` (each member's adjusted average x CPI of the date /
its row's `consumer_price_index_value`), the three `price_earnings_..._ratio` columns (market value / each
earnings total), `consumer_price_index_value` (US CPI of the latest month on or before the date with a
value), `member_count`, `members_used_count`, `members_without_shares_count`,
`members_under_ten_years_count`, `currency_code` and `ingested_timestamp`. Every column SHALL carry a
Unity Catalog description.

#### Scenario: One company, two listings
- **WHEN** Alphabet's GOOGL and GOOG both have prices on a date
- **THEN** Alphabet counts once, at the close of its more traded listing

#### Scenario: A member without a share count
- **WHEN** a current member has neither share count on its valid filing row
- **THEN** it is in no total of that date and `members_without_shares_count` counts it

### Requirement: Market climate signals
`gold_analytics_gateway.monitor_signal_daily` SHALL have one row per `signal_date`, `monitor_code`,
`lens_code` and `signal_code`, with display names, `is_yes`, `band_code`, `measured_value`,
`threshold_value`, `reason_text`, `yes_count`, `action_name` and `ingested_timestamp`, each with a Unity
Catalog description. For monitor `market_climate` and each lens (`long_run`, `modern`) it SHALL have:
`too_expensive` (yes when the 10-year inflation-adjusted P/E is above 22 for the long run, 30 for modern;
bands at 16 / 22 and 22 / 30); `fed_in_the_way` (yes when the latest change of the Fed target upper bound
on or before the date was a hike less than 6 months before it); `market_going_up` (yes when `^GSPC`
closes above its 200-day average; band green above with a slope of at least 0.002, yellow above with a
lower slope, red at or below); and, on dates with all three answers, a `climate` row named "Market
climate long run" or "Market climate modern" whose `yes_count` counts the yes answers and whose light is
red for 2 or 3 (sell), yellow for 1 (buy and hold), green for 0 (strong buy).

#### Scenario: Two yes answers
- **WHEN** on a date the P/E is 27.4, the latest Fed change was a cut and `^GSPC` is above its average
- **THEN** the long run climate is red with `yes_count` 2 and action sell, and the modern climate is
  yellow with `yes_count` 1 and action buy and hold

#### Scenario: A hike, then six months without change
- **WHEN** the target was raised on 2023-07-27 and not changed again until 2024-09-19
- **THEN** `fed_in_the_way` is yes up to 2024-01-26 and no from 2024-01-27

#### Scenario: Before the first member price
- **WHEN** a date has a Fed answer and a trend answer but no index valuation
- **THEN** it has those answer rows and no `too_expensive` or `climate` row
