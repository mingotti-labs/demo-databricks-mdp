## MODIFIED Requirements

### Requirement: Yield Deep Dive
The Currency Monitor dashboard SHALL have a page "Yield Deep Dive" with a base currency selector (the Australian dollar by
default, the US dollar the other choice) and a table of the main currencies' countries ranked by the short-term interest
rate in percent plus the change of the currency's value in the base over the last 252 trading days in percent (none for
the base itself), showing for each the short-term rate and its reading date, the 10-year yield when it has one, the
currency change, the distance from its 200-day average and the sum. A country without a current short-term rate or
without a year of history SHALL not be ranked.

The page SHALL also have a chart of the US 10-year Treasury yield against the short-term US Treasury yields the user
picks (one or several of 3 months, 1 year, 2 years and 3 years; all four by default), over a history range chosen on the
page (the same options as the other dashboards, 36 months by default), with the spread (10-year minus the short-term
yield, percentage points) in the tooltip.

#### Scenario: Ranking in Australian dollars
- **WHEN** the base is the Australian dollar and the Australian short-term rate is 4.60 and every other currency has lost
  value against the Australian dollar over the year
- **THEN** the Australian dollar ranks first with a sum of 4.6 and the table shows the change of every other currency as
  negative

#### Scenario: Ranking in US dollars
- **WHEN** the user picks the US dollar as the base
- **THEN** the same table is shown with each currency's change against the US dollar and the US dollar with no change

#### Scenario: The 10-year against the 2-year
- **WHEN** the user picks only the 2-year and a 12-month range
- **THEN** the chart shows two lines, the 10-year and the 2-year, over the last 12 months, and the tooltip on 2026-11-05
  shows 4.46 for the 2-year and the 10-year minus 4.46 as the spread

#### Scenario: Several short-term yields
- **WHEN** the user picks the 3-month and the 3-year
- **THEN** the chart shows the 10-year and both, each in its own colour
