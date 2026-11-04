## 0. Before

- [x] 0.1 iac `gold-analytics-gateway-grants` (#79) implemented and applied; grants checked on both catalogs

## 1. Thresholds

- [x] 1.1 `src/common/market_climate.py`: lines, bands, Fed window, flat slope, light and action per yes
      count; tests in `tests/common/test_market_climate.py`

## 2. Gold pipeline

- [ ] 2.1 `resources/pipelines/gold_analytics_gateway.pipeline.yml` and `src/layers/gold/analytics_gateway/`
- [ ] 2.2 `index_valuation_daily.py` (D1-D3) with full described schema (D7)
- [ ] 2.3 `monitor_signal_daily.py` (D4) with full described schema (D7)

## 3. Run job and patterns

- [ ] 3.1 `run_investments`: `gold`, `verify_gold`, `tag_patterns` after gold (D5)
- [ ] 3.2 `src/common/design_patterns.yml`: `gold_analytics_gateway: gold_materialized_view_sql`; register entry

## 4. Verification

- [ ] 4.1 `verification/verify_gold_market_climate.py`: both keys unique; latest valuation day has
      `members_used_count` >= 480 and a P/E (10-year, inflation-adjusted) between 20 and 60; every day with
      a valuation has two climate rows; `yes_count` equals the yes answers and the light follows it; Apple's
      market value on the latest day equals its close x shares recomputed from silver

## 5. Naming and docs

- [ ] 5.1 NAMING.md (gold naming no longer TBD), `silver.md` endings (`_text`), CLAUDE.md "Sources" (gold),
      `data-sources.md` / register as needed

## 6. Run and check in dev

- [ ] 6.1 Draft PR deploy-dev; `run_investments verify=true` (polled); results against story probe P1
      (record as a probe)
- [ ] 6.2 Descriptions visible in Unity Catalog for both tables

## 7. After merge

- [ ] 7.1 prd: CI runs `investments`; prd = dev for the latest valuation day and both lights
