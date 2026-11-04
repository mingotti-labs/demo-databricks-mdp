## 0. Evidence (done in the proposal PR)

- [x] 0.1 Probes P1-P4 in `references/poc/market-climate/` with results; rows in
      `references/docs/registers/probes.md`

## 1. Figure

- [ ] 1.1 `data/portfolio/concept_mapping.csv`: `weighted_average_shares_basic_count,1,us-gaap,WeightedAverageNumberOfSharesOutstandingBasic`
- [ ] 1.2 `src/common/investments.py`: the figure with kind `period`; tests (`tests/common/test_investments.py`
      knows the new kind)
- [ ] 1.3 `company_fundamentals.py`: the `period` pick (D1) and the pass-through column; table comment

## 2. Verification

- [ ] 2.1 `verify_silver_domain_investments.py`: MA's latest row has `weighted_average_shares_basic_count`;
      current members with neither count stay at or under 5

## 3. Run and check in dev

- [ ] 3.1 Draft PR deploy-dev; `run_portfolio`, `run_sec`, `run_investments verify=true` in that order
      (`cicd/run_dev.py`)
- [ ] 3.2 Re-run P2's share query: members with neither count, before 42 (record the number)

## 4. Docs

- [ ] 4.1 CLAUDE.md "Silver Domain investments" and the SEC entry; `data-sources.md` if it lists figures

## 5. After merge

- [ ] 5.1 prd: CI runs `investments`, `portfolio`; then `run_sec`, `run_investments` by hand; prd = dev counts
