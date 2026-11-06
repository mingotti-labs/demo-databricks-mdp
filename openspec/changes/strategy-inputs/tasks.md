## 1. Inputs (D1, D3)

- [x] 1.1 `data/portfolio/concept_mapping.csv`: figure `revenue`, five concepts in the D1 priority; `FIGURES` entry
      `("revenue", "duration", "USD")` and a `COMPANY_FUNDAMENTALS_COMMENTS` description in `src/common/investments.py`.
      Check: the unit tests of the settings files and the figure list pass
- [x] 1.2 `data/portfolio/benchmarks.csv`: SQQQ, PSQ, SH, SDS, SPXU, kind `bear_fund`; pinned counts in
      `verification/bronze_checks/portfolio.yml` (benchmarks and concept mapping) updated

## 2. Gold (D2)

- [x] 2.1 `valuation_daily_index_member`: `revenue_trailing_twelve_months_amount` and `price_to_sales_ratio`, with
      descriptions; the index P/E query untouched. Check: unit tests of the query text, if any; `cicd/build_dashboards.py --check`
      still passes (no dashboard change)

## 3. Run and check in dev

- [ ] 3.1 Draft PR deployed to dev; one run at a time: `run_portfolio`, `run_sec` (every company refetched once),
      `run_yahoo`, `run_investments verify=true`
- [ ] 3.2 Probe P4 (dev, saved under `references/poc/strategies/`): share of current members with a revenue on the latest
      filing; one company's price-to-sales by hand from its filing and price; the five funds' first and last price dates;
      the index P/E of the latest day unchanged against before the change
- [ ] 3.3 Quota read (no change expected, 484)

## 4. After merge

- [ ] 4.1 prd: CI runs `investments`, `portfolio`, `sec`, `yahoo`; the user starts one more `run--investments--prd`;
      P4 on prd matches dev
- [ ] 4.2 Archive; planning design status updated; memory updated
