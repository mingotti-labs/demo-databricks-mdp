## 1. Shared page

- [x] 1.1 `src/common/company_page.py` (page, price chart, datasets, parameters); the Market Climate builder uses it; its dashboard file
      and the Genie file are byte-identical (`build_dashboards.py --check` lists only the dashboards that gain the page)
- [x] 1.2 The Inflation-Deflation, Currency and Strategy builders add the page, the datasets, the parameters and the date binding;
      generated files; tests (page identical in every dashboard, datasets and parameters, date filter binding)

## 2. Run and check in dev

- [x] 2.1 Draft PR deployed (stacked on #192, see Cross-repo dependencies); the four dev dashboards have the page
- [x] 2.2 The user checks the page in the Strategy Monitor (looks fine)

## 3. After merge

- [ ] 3.1 prd: CI deploys; the user opens the tab in each dashboard
- [ ] 3.2 Archive; memory
