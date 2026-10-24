## Why

The dividend portfolio story (design: `demo-databricks-planning`,
`docs/superpowers/specs/2026-10-24-dividend-portfolio-story-design.md`) depends
on free sources whose limits are unknown. The S&P 500 list could come from FMP
or Wikipedia, dividend pay dates from FMP or an estimate, and Yahoo may not
allow about 500 tickers from Databricks serverless. These must be checked before
the first source change is designed, so no change is built on a guess.

## What Changes

- Run throwaway probes in dev on Databricks serverless, and record what they
  show in this change's `design.md` and in
  `references/docs/registers/probes.md`:
  - each source's web address can be reached from serverless
  - the current metastore table count against the 500-table limit
  - the Wikipedia S&P 500 page can be parsed
  - FMP on the free plan, with the user's key read from the `fmp` secret scope:
    the S&P 500 list, dividend pay dates, the daily limit, and a cheaper way
    than one call per ticker
  - SEC `companyfacts` coverage of the figures the ranking needs, for a sample
    of companies
  - Yahoo (`yfinance`): about 500 tickers fetched without being blocked, the
    full dividend history, and whether options are listed
- Decide, from the results, the S&P 500 list source (FMP or Wikipedia) and the
  pay-date source (FMP or estimate). Record the decision for change 2 onwards.
- The probe scripts are kept in `references/poc/dividend-portfolio/` (outside
  the bundle upload, like the rest of `references/`), so they can be read and
  rerun. No pipeline, job, table or bundle change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This change only records findings (`skip_specs: true`).

## Impact

- Docs: this change's `design.md` (results), `references/docs/registers/probes.md`
  (one new section).
- New folder `references/poc/dividend-portfolio/`: one script per probe and a
  short README.
- Dev workspace: the scripts uploaded to a folder under the user's home, run as
  one-time serverless jobs; the folder is removed afterwards. No tables are
  created.
- FMP: at most 15 calls of the 250 a day. SEC: about 15 requests. Yahoo: about
  1,000 requests in one run. Free Edition allows one workload at a time, so the
  probes run one after another.

## Cross-repo dependencies

Depends on `dividend-portfolio-schemas` in `demo-databricks-iac` (applied and
archived 2026-10-25): the FMP probe reads the key from the `fmp` secret scope
that change created.

## Model

Opus: the probes have no template, and their results decide the shape of the
first source changes.
