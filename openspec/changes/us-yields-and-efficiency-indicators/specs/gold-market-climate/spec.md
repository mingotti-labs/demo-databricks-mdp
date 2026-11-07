## MODIFIED Requirements

### Requirement: Company Deep Dive in every monitor dashboard
The Inflation-Deflation Monitor and the Strategy Monitor dashboards SHALL each have the same *Company Deep Dive* page as
the Market Climate Monitor (a company selector and a range selector, the last close, change on the day, 52-week high and
low, the close with Bollinger bands, and the steps to the trailing and 10-year inflation-adjusted P/E), built from one
shared definition, and the dashboard's as-of date SHALL drive the page's date-dependent datasets as it does on the Market
Climate Monitor. The Currency Monitor SHALL not have the page.

#### Scenario: The same page in every dashboard
- **WHEN** the monitor dashboards are generated
- **THEN** the Market Climate, Inflation-Deflation and Strategy dashboards each have a page named company-deep-dive with
  identical widgets, and the Currency Monitor has none

#### Scenario: The date at the top moves the page
- **WHEN** a user changes the as-of date of the Strategy Monitor
- **THEN** the Company Deep Dive shows the figures of the latest day on or before it
