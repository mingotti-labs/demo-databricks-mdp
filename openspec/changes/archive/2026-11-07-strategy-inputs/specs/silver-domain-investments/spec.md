## ADDED Requirements

### Requirement: Revenue per filing
`company_fundamentals` SHALL have a `revenue` column: the filing's revenue in US dollars, trailing twelve months to its
period end by the same rule as `net_income`, from the highest-priority concept of figure `revenue` in the `portfolio`
concept mapping that has a value in that filing (`Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`,
`RevenuesNetOfInterestExpense`, `SalesRevenueNet`, `RevenueFromContractWithCustomerIncludingAssessedTax`), empty when
none has. The concept map SHALL name the concept used, and the column SHALL carry a Unity Catalog description.

#### Scenario: A company that switched concept
- **WHEN** a company's 2017 10-K reports `SalesRevenueNet` and its 2025 10-K reports only
  `RevenueFromContractWithCustomerExcludingAssessedTax`
- **THEN** both rows have a `revenue`, and the concept map names the concept each filing used

#### Scenario: Total revenue first
- **WHEN** a filing reports both `Revenues` and `RevenueFromContractWithCustomerExcludingAssessedTax`
- **THEN** `revenue` is the `Revenues` value
