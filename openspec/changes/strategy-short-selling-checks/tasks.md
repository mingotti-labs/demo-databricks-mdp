## 1. Query

- [ ] 1.1 `ds_short_checks` in `strategy_queries.py` (D1, D2); run on dev read-only: NVDA listed on the weeks to
  2026-10-23 to 2026-11-20 with a red price-to-sales check from 2026-11-06 (as-of date set to each Friday)

## 2. Page and agent

- [ ] 2.1 Table "Setups started: rule checks" on the Short Selling page in `strategy_dashboard.py`, with the light note;
  add the dataset to `DATE_DATASETS`; generated dashboard; tests
- [ ] 2.2 Genie example (D4); generated agent file; every example SQL runs in dev

## 3. Run and check in dev

- [ ] 3.1 Draft PR deployed (deploy-dev pass); strategy dashboard queries run in dev (`p3_test_queries.py`); Genie
  benchmark evaluation on dev
- [ ] 3.2 The user checks the page in dev

## 4. After merge

- [ ] 4.1 prd: CI deploys; queries and benchmark evaluation on prd; the user checks the page
- [ ] 4.2 Archive; planning story `strategy-002`; memory
