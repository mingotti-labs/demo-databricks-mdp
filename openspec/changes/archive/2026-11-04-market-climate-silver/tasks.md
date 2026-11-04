## 1. Probe

- [x] 1.1 P1: partial `schema=` rejected, full list works and comments reach Unity Catalog (design.md D4,
      `references/poc/market-climate-silver/p1_result.txt`, probes register); leftovers dropped with approval

## 2. Benchmark

- [x] 2.1 `data/portfolio/benchmarks.csv`: `^GSPC,S&P 500 index,market_index,`; test or check that
      reads the file still passes

## 3. company_fundamentals

- [x] 3.1 The 10-year window (D1) and CPI (D2): `consumer_price_index_value`,
      `earnings_ten_year_average_amount`, `earnings_ten_year_average_inflation_adjusted_amount`,
      `earnings_year_count`, with column descriptions (D4)

## 4. price_indicator_daily

- [x] 4.1 New view (D3), one file named after the table, descriptions on every column

## 5. Naming

- [x] 5.1 `references/docs/medallion/silver.md` endings table: `_ratio`, `_value`

## 6. Verification

- [x] 6.1 `verify_silver_domain_investments.py`: key uniqueness for `price_indicator_daily`
      (`listing_id`, `price_date`); `^GSPC` has prices before 2000 and a 200-day average on its latest
      row; Apple's row for its fiscal 2025 10-K (the 10 years 2016-2025, as in the story's probe P1) has `earnings_year_count`
      10, `earnings_ten_year_average_amount` about 76.35 bn and
      `earnings_ten_year_average_inflation_adjusted_amount` about 87.55 bn (story probe P1 in that
      row's money, CPI 324.8), within 0.05 bn

## 7. Run and check in dev

- [x] 7.1 Draft PR deploy-dev; `run_portfolio`, `run_yahoo`, `run_investments verify=true` in that order,
      each `--no-wait` and polled
- [x] 7.2 Descriptions visible in Unity Catalog (`DESCRIBE TABLE`) for the new columns

## 8. Docs

- [x] 8.1 CLAUDE.md "Silver Domain investments"; `data-sources.md` if it lists the domain tables

## 9. After merge

- [x] 9.1 prd: CI runs `investments`, `portfolio`; then `run_yahoo`, `run_investments` by hand; prd = dev
      for the Apple row and `^GSPC`
