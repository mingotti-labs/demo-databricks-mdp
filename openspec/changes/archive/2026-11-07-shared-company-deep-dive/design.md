## Context

- The page was built in `market-climate-dashboard` inside `market_climate_dashboard.py` with five datasets in
  `market_climate_queries.py`: `ds_company_names`, `ds_company_check`, `ds_company_price`, `ds_company_figures`,
  `ds_range_options`. Three of them take the dashboard's as-of date; the company and the price range are parameters.
- Each generated dashboard has its own datasets, parameters and a global filter page binding its date datasets to `as_of_date`.

## Goals / Non-Goals

**Goals:** the same page in every monitor dashboard, defined once.

**Non-Goals:** drill-through, links from tables, a separate Company dashboard, new queries.

## Decisions

### D1. One shared module, copies per dashboard

`company_page.py` holds the page, its price chart and the dataset names and parameters; a dashboard adds them. A dashboard is a
self-contained file, so each carries its copy of the five datasets (queries run only when the page is opened). Rejected: one
separate Company dashboard (needs links, which need the target's id per environment and an undocumented URL syntax); drill-through
(Databricks fills only filters of a dataset the source and target share; every table here has its own dataset and the company is
chosen by a parameter; the user also could not find a setting for it).

### D2. Date filter

The date-bound company datasets join each dashboard's `DATE_DATASETS`, so the dashboard's as-of date filter drives the page the same
way as on the Market Climate dashboard (the latest day on or before it).

### D3. The move changes nothing

The Market Climate dashboard file and the Genie agent file stay byte-identical (checked with `build_dashboards.py --check`); the
other dashboards only gain the page. A test checks the page JSON is identical in every dashboard, that each carries the datasets with
their parameters and that each date filter drives the date-bound datasets.

## Risks / Trade-offs

- [Four copies of five datasets] → generated from one module; queries run only when the page is opened.
- [The company is picked twice if the user comes from another page] → accepted; no click-through (see D1).
- [All pull requests deploy to one shared dev bundle] → this change is stacked on `strategy-monitor-dashboard`; merge that first.

## Migration Plan

Merge after #192; CI deploys the dashboards in prd; the user opens the Company Deep Dive tab in each. Rollback: revert.

## Open Questions

None.
