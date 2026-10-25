## Context

See proposal.md. Probe P3 (`dividend-portfolio-probes`, 2026-10-25) parsed the
page on dev serverless: 503 rows, 500 distinct CIKs, every date parses, and
`read_html` turns CIK into a number (leading zeros lost). The page's "Selected
changes" table is gone, so membership history can only come from our own
snapshots. The closest existing sources are `iso` and `geonames` (one static
fetch, Materialized View, bronze full pattern, change-feed Landing).

## Goals / Non-Goals

**Goals:**
- Land the index list with its sector, sub-industry, date added and CIK, and
  keep its membership history from the first load.

**Non-Goals:**
- Joining share classes to a company, converting symbols to Yahoo's form, and
  casting dates: those are `silver_investments` work.
- Silver Normalised, SCD1, SQL variants, a quarantine table.

## Decisions

- **D1 Parse with pandas `read_html(flavor="lxml", attrs={"id": "constituents"})`.**
  Pipeline dependencies `requests` and `lxml`. `flavor` is set explicitly: with
  a missing table pandas falls back to another parser and hides the real error
  (probe P3, first attempt). CIK is read with `converters={"CIK": str}` and
  `zfill(10)`; every column is kept as text. Rejected: BeautifulSoup (one more
  dependency for no gain); MediaWiki's API (wikitext, not a table).
- **D2 Source-faithful raw.** Symbols keep dots (`BRK.B`), dates and `founded`
  stay text. The Silver domain converts (to Yahoo's `BRK-B`, to dates).
- **D3 Key is `symbol`.** Distinct `symbol` over the real page is checked before
  the pipeline is written (task 1.2); the probe only confirmed distinct CIK.
  A duplicate would add a quarantine table, as ISO did.
- **D4 Bronze full pattern**, as `iso`: `ingested_timestamp` in the raw
  Materialized View, a private snapshot view that drops it, SCD2 target with
  `pipelines.reset.allowed=false` and change data feed. The snapshot Auto CDC
  closes a version when a symbol disappears, which is the membership history.
- **D5 Silver Landing via `land_changes`**, key `symbol`, in its own silver
  pipeline (`silver--wikipedia--<target>`), as every source.
- **D6 Run job without the one-off `reset` task** (iso's exists only for the
  rollout of the pattern). Tasks: bronze, verify_bronze, silver, verify_silver,
  tag_patterns, same conditions as `run_iso`.
- **D7 Bundle variables.** `wikipedia_sp500_url` (the page) and
  `http_user_agent` (`mdp handsonessential@gmail.com`: Wikimedia's policy asks
  for a contact; the SEC change reuses it). Both in `cicd/databricks/free.yml`
  and `standard.yml`, then `apply_edition.py`. The pipeline reads them through
  `configuration`, as iso does.
- **D8 Verification.** `bronze_checks/wikipedia.yml` with `keys: [symbol]`,
  `columns: [ingested_timestamp]`, `reference_rows` left out (the index size
  moves), plus a floor of 480 rows in the helper's own scenario; a Silver
  Landing entry and `wikipedia` in `SOURCES_WITH_INGESTED_TIMESTAMP`. The
  second-run no-change check is run once by hand in dev (task 3.3).
- **D9 CI.** The job keeps `ci_auto_run` default (a free source), so a merge
  that touches it runs it after the tst/prd deploy; prd's first run is by CI.

## Risks / Trade-offs

- [Wikipedia changes the table layout or id] → the helper fails loudly (no
  table, or missing column) and the pipeline fails, as designed; fix in a small
  change. Verification asserts the column set.
- [Wikipedia blocks the pipeline's IP] → none seen from serverless (P1, P3);
  the `User-Agent` follows Wikimedia's policy.
- [Page vandalism or a transient edit shows a company leaving for a week] →
  the SCD2 shows a close and a reopen; later Silver can ignore gaps under a
  week if it matters. Accepted for a weekly demo.
- [Wikipedia is not the licence-free index source] → text is CC BY-SA 4.0;
  attribution as a table comment, as ISO does.

## Migration Plan

Deploy to dev, run `run_wikipedia` with `verify=true`, run once more with no
change and confirm no version is written. tst/prd: CI deploys on merge; the
tables are created on the first run. Rollback: remove the resources; the three
schemas stay (iac).
