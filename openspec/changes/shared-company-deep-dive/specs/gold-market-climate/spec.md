## ADDED Requirements

### Requirement: Company Deep Dive in every monitor dashboard
The Inflation-Deflation Monitor, the Currency Monitor and the Strategy Monitor dashboards SHALL each have the same *Company Deep
Dive* page as the Market Climate Monitor (a company selector and a range selector, the last close, change on the day, 52-week high
and low, the close with Bollinger bands, and the steps to the trailing and 10-year inflation-adjusted P/E), built from one shared
definition, and the dashboard's as-of date SHALL drive the page's date-dependent datasets as it does on the Market Climate Monitor.

#### Scenario: The same page in every dashboard
- **WHEN** the four monitor dashboards are generated
- **THEN** each has a page named company-deep-dive with identical widgets, and the Market Climate Monitor's file is unchanged by the move

#### Scenario: The date at the top moves the page
- **WHEN** a user changes the as-of date of the Strategy Monitor
- **THEN** the Company Deep Dive shows the figures of the latest day on or before it
