## 1. Rules and queries

- [ ] 1.1 `strategy.py`: `EFFICIENT_STOCKS_CODE`, `EFFICIENCY_MIN`, `EFFICIENT_VOLUME_MIN`, `efficient_stock_passes`; tests
- [ ] 1.2 `ds_efficient_summary` and `ds_efficient_closest` in `strategy_queries.py`; run on dev and prd read-only (probe)

## 2. Page and agent

- [ ] 2.1 Page "Efficient Stocks" in `strategy_dashboard.py`; date binding; generated dashboard; tests
- [ ] 2.2 Genie: instructions, examples, one benchmark; generated agent file; every example and benchmark SQL runs in dev

## 3. Run and check in dev

- [ ] 3.1 Draft PR deployed; all dashboard queries run in dev (`p3_test_queries.py`); Genie benchmark evaluation passes
- [ ] 3.2 The user checks the page in dev

## 4. After merge

- [ ] 4.1 prd: CI deploys; queries and benchmark evaluation on prd; the user checks the page
- [ ] 4.2 Archive; planning story `strategy-004` and README; memory
