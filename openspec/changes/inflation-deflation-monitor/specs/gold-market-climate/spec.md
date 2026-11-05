## MODIFIED Requirements

### Requirement: Market climate dashboard
A dashboard "Market Climate Monitor" SHALL read the gold tables of its target's catalog and have four pages, each
with a date defaulting to the latest day with a climate row: *Climate* (the "Climate as of" date, the latest
date of each input, a traffic light per climate with its yes count, then the light history, the P/E, Fed
target (with the hike and cut periods shaded) and S&P 500 trend charts, then the answers table); *Climate Deep Dive* (the day's index row, the 10 members
with the largest and the 10 with the smallest effect with their "without" ratio, the members left out with
their reason, all members filterable by sector and use, and the checks that the member rows add up to the
index row); *Company Deep Dive* (a company selector and range selector, the last close, change on the day,
52-week high and low, the close with Bollinger bands of 20 days and 2 standard deviations, and the steps from
price and filing to the trailing and the 10-year inflation-adjusted P/E); and *Sector Deep Dive* (a sector selector, the sector's P/E against the index P/E, the index P/E
without the sector, and the sector's members by effect). Sector SHALL come from
`silver_domain_investments.company` by `company_id`.

#### Scenario: Checking a light
- **WHEN** the user opens Climate Deep Dive for the latest day
- **THEN** the member sums shown equal the index row and the largest effects explain the ratio
