## 1. US yields (D1)

- [x] 1.1 `DGS3MO`, `DGS1`, `DGS2`, `DGS3` in `fred_series.SERIES` and `investments.RATES` (codes and names of D1); tests
- [x] 1.2 `verify_silver_domain_investments` covers them through `RATES` (no change expected; check)

## 2. Strategy 004 indicators (D4)

- [x] 2.1 `price_indicator_daily`: the 13 columns with their descriptions; the 60-day windows and the previous close
- [x] 2.2 Query run on prd's prices before the deploy (probe E4: row count equals price_daily, true range never below the range, highest r60 13.31 and tr60 10.29 as probe E3); dev after the run: highest r60 13.32, tr60 10.29 (`p2_dev_after_run.txt`)

## 3. Yield Deep Dive chart and the Currency Monitor (D2, D3)

- [x] 3.1 `ds_us_yield_curve` in `currency_queries.py`; the chart, the maturity filter and the history range selector on
      the Yield Deep Dive; Genie literal for the new parameter; generated dashboard and agent files; tests
- [x] 3.2 The Currency Monitor without the Company Deep Dive; the shared page test covers three dashboards
- [x] 3.3 Every dashboard and Genie example query runs in dev (58 of 58, `references/poc/us-yields/p3_dashboard_queries_dev.txt`)

## 4. Run and check in dev

- [x] 4.1 Draft PR #197 deployed; `run_fred` then `run_investments verify=true` in dev succeeded; the four yields have full history (3-month from 1981, 2-year from 1976, 1- and 3-year from 1962)
- [x] 4.2 Genie benchmark evaluation in dev passes (17 of 17); quota read: 496 of 500 (no table added by this change; the earlier 488 was out of date)
- [x] 4.3 The user checks the Yield Deep Dive in dev (chart looks ok)

## 5. After merge

- [x] 5.1 prd: CI deployed and ran the units; yields from 1962/1976/1981 to 2026-11-05, 58 of 58 queries (`p4_dashboard_queries_prd.txt`), Genie 17 of 17; the user said go
- [x] 5.2 Archive; planning story `strategy-004` (indicators done, units of the efficiency ratio); memory
