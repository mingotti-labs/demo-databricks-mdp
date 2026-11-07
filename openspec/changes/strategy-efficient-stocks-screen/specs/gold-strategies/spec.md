## ADDED Requirements

### Requirement: Strategy 004 efficient stocks screen
The Strategy Monitor SHALL have a page "Efficient Stocks" showing, for the latest `^GSPC` trading day on or before the
dashboard's date, the screen of strategy 004 over that day's S&P 500 members: a stock passes when its efficiency ratios
r60 and tr60 (`price_indicator_daily`) are both 15 or more and its 60-day average volume is above 200,000 shares. The page
SHALL show the rules, the number of members screened and passing, and the 20 members with the highest r60 with r60, tr60,
the 60-day change, the average range and true range as a share of the close, the average volume and a light per rule. The
story's smoothness rules SHALL be listed as not checked. The screen SHALL add no rows to `strategy_daily_event`. The Genie
agent SHALL carry the screen rules in its instructions, the page's queries as examples and a benchmark asking which stocks
are closest to passing.

#### Scenario: No stock passes
- **WHEN** no member has r60 and tr60 of 15 or more on the day
- **THEN** the summary says no stock passes and the table lists the 20 members with the highest r60, PTC first on
  2026-11-06 with r60 13.3

#### Scenario: One ratio above the threshold
- **WHEN** a member has r60 16 and tr60 14 and an average volume of 2 million
- **THEN** it is listed with a yellow efficiency light, a green volume light and does not pass

#### Scenario: A past day
- **WHEN** the user sets the dashboard's date to a past day
- **THEN** the page shows the screen of the latest trading day on or before it
