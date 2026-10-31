## 1. Before building

- [ ] 1.1 iac `silver-domain-investments-schema` applied: `silver_domain_investments`
      exists in `mdp_dev` and `mdp_prd` with the grants `silver_investments` had,
      and `silver_investments` is gone (`databricks schemas list`)
- [ ] 1.2 Probe P1 (design.md): coverage of the new concepts per current CIK;
      scripts and result in `references/poc/silver-domain-investments/`, row in
      the probes register, result in design.md
- [ ] 1.3 Table quota read before the first deploy: stop and ask if above 460
      (28 slots to add, stop line 488)

## 2. Naming and mapping

- [ ] 2.1 NAMING.md (schema table row, Silver Domain table naming, timestamp
      status) and `references/docs/medallion/silver.md` say `silver_domain_<domain>`;
      `grep -rn silver_investments` in docs finds only archived changes
- [ ] 2.2 The ten mapping rows in `data/portfolio/concept_mapping.csv`; dev:
      `run_portfolio`, then `run_sec`; the new concepts appear in
      `mdp_dev.silver_landing.sec__company_facts`

## 3. Shared logic

- [ ] 3.1 `src/common/investments.py`: figure list with instant or duration,
      concept choice (priority, latest filing), duration check, special-dividend
      rule, rate list; unit tests, including that the figure list matches
      `concept_mapping.csv`

## 4. Pipeline

- [ ] 4.1 Pipeline resource `silver_domain_investments` and folder
      `src/layers/silver/domain/investments/`; `databricks bundle validate` passes
- [ ] 4.2 `company` and `index_membership`; dev: 500 companies in the index,
      `GOOGL` and `GOOG` on one row
- [ ] 4.3 `price_daily` and `options_activity`; dev: row counts equal Landing's
      (prices per symbol and date, options per symbol)
- [ ] 4.4 `dividend`; dev: row count equals Landing's dividends, `amount_aud`
      set on every dividend since 2023-01-03, a spot check of one real and one
      estimated pay date, the special dividends listed and checked by eye
- [ ] 4.5 `market_rate_daily`; dev: six rate codes, latest values equal Landing's
      (cash rate 4.60, 10-year 4.98 on 2026-10-29)
- [ ] 4.6 `company_fundamentals`; dev: one row per company and filing date,
      contiguous validity ranges ending 9999-12-31, `net_income` on the current
      row for at least 95% of index companies, the ExxonMobil successor has the
      predecessor's filings, three companies checked by hand against their
      latest 10-Q and 10-K (one bank, one with the liabilities fallback, one
      trailing-twelve-months sum)

## 5. Job and verification

- [ ] 5.1 `run_investments` with the `verify` parameter and
      `verification/verify_silver_domain_investments.py`; dev run with
      `verify=true` passes; one deliberate failure (a check pointed at a
      missing symbol) fails and names it
- [ ] 5.2 Design pattern register entry and `design_patterns.yml`; the register
      tests pass

## 6. Documentation

- [ ] 6.1 CLAUDE.md (Silver Domain entry), `references/docs/registers/data-sources.md`
      if it lists consumers, design.md dev results; all tests pass
      (`uv run python -m pytest`)
- [ ] 6.2 The story's design doc in `demo-databricks-planning`: steps 7 and 8
      done, step 9 split (this change, then gold), the schema renamed
