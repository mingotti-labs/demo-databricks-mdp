## ADDED Requirements

### Requirement: Index member valuation per day
`gold_analytics_gateway.valuation_daily_index_member` SHALL have one row per `index_code`, `valuation_date`
and `company_id` for every current index member (one listing per company, the most traded over its last 60
price rows) on every valuation day, used or not. It SHALL carry the trace (`listing_id`, `price_date`,
`filing_valid_from_date`), the inputs (`price_close`, `share_count`, `share_count_source_code`
`cover_page` or `weighted_average`, `earnings_trailing_twelve_months_amount`,
`earnings_ten_year_average_amount`, `earnings_year_count`, `filing_consumer_price_index_value`,
`consumer_price_index_value`), `earnings_ten_year_average_inflation_adjusted_amount` (the stored average x
the day's CPI / the filing's CPI), `market_value_amount`, `is_used`, and `exclusion_reason_code`, the first
failing of `no_recent_price`, `no_filing`, `no_share_count`, `no_net_income`, `no_ten_year_average`,
`no_consumer_price_index`. For used members it SHALL carry, on the 10-year inflation-adjusted ratio,
`market_value_share_ratio`, the member's own
`price_earnings_ten_year_average_inflation_adjusted_ratio`, `price_earnings_without_member_ratio` (the index
ratio computed without the member) and `price_earnings_effect_ratio` (index ratio minus the "without"
ratio). Every column SHALL carry a Unity Catalog description.

#### Scenario: A member that pushes the P/E up
- **WHEN** a used member's own ratio is above the index ratio and it holds a large share of market value
- **THEN** its "without" ratio is below the index ratio and its effect is positive

#### Scenario: A member left out
- **WHEN** a current member has a price on a day but no share count on its valid filing row
- **THEN** it has a row with `is_used` false, `exclusion_reason_code` `no_share_count` and no position figures

### Requirement: Market climate dashboard
A dashboard "Market climate" SHALL read the gold tables of its target's catalog and have three pages, each
with a date defaulting to the latest day with a climate row: *Climate* (the "Climate as of" date, the latest
date of each input, both lights with their three answers and reasons, the light history, and the P/E, Fed
target and S&P 500 trend charts with their lines); *Climate Deep Dive* (the day's index row, the 10 members
with the largest and the 10 with the smallest effect with their "without" ratio, the members left out with
their reason, all members filterable by sector and use, and the checks that the member rows add up to the
index row); and *Sector Deep Dive* (a sector selector, the sector's P/E against the index P/E, the index P/E
without the sector, and the sector's members by effect). Sector SHALL come from
`silver_domain_investments.company` by `company_id`.

#### Scenario: Checking a light
- **WHEN** the user opens Climate Deep Dive for the latest day
- **THEN** the member sums shown equal the index row and the largest effects explain the ratio

## MODIFIED Requirements

### Requirement: Index valuation per day
`gold_analytics_gateway.valuation_daily_index` SHALL have one row per `index_code` (`SP500`) and
`valuation_date`, for each `^GSPC` price date from the first date a current member has a price, summed
from the used rows of `valuation_daily_index_member` for that day. The day's
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

#### Scenario: Totals from the member rows
- **WHEN** the used member rows of a day are summed
- **THEN** the counts equal the day's index row exactly and the amounts to the cent

### Requirement: Market climate signals
`gold_analytics_gateway.monitor_daily_signal` SHALL have one row per `signal_date`, `monitor_code`,
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
