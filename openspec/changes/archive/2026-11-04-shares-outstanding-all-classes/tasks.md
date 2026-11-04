## 0. Evidence (done in the proposal PR)

- [x] 0.1 Probes P1-P4 in `references/poc/market-climate/` with results; rows in
      `references/docs/registers/probes.md`

## 1. Figure

- [x] 1.1 `data/portfolio/concept_mapping.csv`: `weighted_average_shares_basic_count,1,us-gaap,WeightedAverageNumberOfSharesOutstandingBasic`
- [x] 1.2 `src/common/investments.py`: the figure with kind `period`; tests (`tests/common/test_investments.py`
      knows the new kind)
- [x] 1.3 `company_fundamentals.py`: the `period` pick (D1) and the pass-through column; table comment

## 2. Verification

- [x] 2.1 `verify_silver_domain_investments.py`: MA's latest row has `weighted_average_shares_basic_count`;
      at least 97% of index companies have a share count on the current row

## 3. Run and check in dev

- [x] 3.1 Draft PR deploy-dev; `run_portfolio`, `run_sec`, `run_investments verify=true` in that order
      (`cicd/run_dev.py`)
- [x] 3.2 Re-run P2's share query: members with neither count, before 42, now 8 (probe P5)

## 4. Docs

- [x] 4.1 CLAUDE.md "Silver Domain investments" and the SEC entry; `data-sources.md` if it lists figures

## 5. After merge

- [x] 5.1 prd: CI runs `investments`, `portfolio`; then `run_sec`, `run_investments` by hand; prd = dev counts
