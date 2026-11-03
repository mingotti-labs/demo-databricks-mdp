## 1. Build

- [x] 1.1 `CPI_RATES` in `src/common/investments.py` with a unit test (codes unique, no
      overlap with `RATES`)
- [x] 1.2 `market_rate_daily.py`: add `is_carried_forward`; CPI rows from FRED and ABS
      Landing (ABS `is_current` only), period start, weekday spine to the latest daily
      date
- [x] 1.3 The SQL cannot run in pytest (no Spark), so it was run on the dev warehouse against
      mdp_dev Landing: 5 series, no weekend dates, no duplicate keys, a Saturday period
      start moves to Monday, latest values 104.34, 103.64, 336.940, 336.298, 338.896

## 2. Verify

- [x] 2.1 `verify_silver_domain_investments.py`: key unique still holds; each CPI code has
      rows; no weekend dates among CPI rows; the first row of each period is not carried
      forward
- [x] 2.2 Dev (run 213406249111980, success, the three new checks passed): compare the latest CPI values with
      Landing (103.64, 104.34, 336.940)

## 3. Docs

- [x] 3.1 `data-sources.md` (fred and abs consumers), `silver.md`, `CLAUDE.md` rates note

## 4. Prd

- [ ] 4.1 After the merge CI runs `run_investments` in prd; check counts against dev; archive
