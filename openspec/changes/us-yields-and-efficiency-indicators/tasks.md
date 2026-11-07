## 1. US yields (D1)

- [ ] 1.1 `DGS3MO`, `DGS1`, `DGS2`, `DGS3` in `fred_series.SERIES` and `investments.RATES` (codes and names of D1); tests
- [ ] 1.2 `verify_silver_domain_investments` covers them through `RATES` (no change expected; check)

## 2. Strategy 004 indicators (D4)

- [ ] 2.1 `price_indicator_daily`: the 13 columns with their descriptions; the 60-day windows and the previous close
- [ ] 2.2 Probe in dev after the run: the gap and too-little-history scenarios on real rows, efficiency ratios equal
      probe P1's for prd's latest day (same formula), run time before and after

## 3. Yield Deep Dive chart and the Currency Monitor (D2, D3)

- [ ] 3.1 `ds_us_yield_curve` in `currency_queries.py`; the chart, the maturity filter and the history range selector on
      the Yield Deep Dive; Genie literal for the new parameter; generated dashboard and agent files; tests
- [ ] 3.2 The Currency Monitor without the Company Deep Dive; the shared page test covers three dashboards
- [ ] 3.3 Every dashboard and Genie example query runs in dev (`p3_test_queries.py`)

## 4. Run and check in dev

- [ ] 4.1 Draft PR deployed; `run_fred` then `run_investments verify=true` in dev; the four yields have full history
- [ ] 4.2 Genie benchmark evaluation in dev passes; quota read (488, no change)
- [ ] 4.3 The user checks the Yield Deep Dive in dev

## 5. After merge

- [ ] 5.1 prd: CI deploys and runs `fred` and `investments`; the user checks the Yield Deep Dive in prd
- [ ] 5.2 Archive; planning story `strategy-004` (indicators done, units of the efficiency ratio); memory
