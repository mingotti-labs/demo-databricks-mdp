## Decisions

- **Business days, not trading days.** No platform table holds exchange calendars, price
  history covers about one year, and the rate series follow bond-market and bank days
  (probed 2026-11-03: weekend rows are 0 for DGS10, FXRUSD and FIRMMCRTD; DFF and the
  Fed target limits run every calendar day). A weekday spine is exchange-neutral and
  enough for a 200-day average of a series that changes once a month. A later change can
  swap the spine for a country calendar without touching the rest.
- **CPI only.** Existing rates keep their rows (the Fed series are source data on weekends).
- **One view, one extra column.** `is_carried_forward` is false for every other rate, so
  the table stays one shape. A separate CPI table would cost two quota slots.
- **Current versions only.** ABS Landing keeps closed versions (a rebase); the view reads
  `is_current` rows. FRED Landing holds one row per date.
- **Period to date.** Monthly `YYYY-MM` is the first of the month; quarterly `YYYY-Qn` is
  the first day of the quarter. Parsed in SQL (`to_date` of the month; quarter number
  times 3 minus 2 for the month).
- **End date.** The latest date of the existing daily rates in the same view, so the end
  is data-driven and the view does not depend on `current_date()`.
- **Series list.** A second list `CPI_RATES` next to `RATES` in `src/common/investments.py`
  (rate code, name, source, series id, unit). `RATES` stays the list of daily rates the
  verification expects to be fresh.

## Risks

- Look-ahead (see the proposal). The flag shows repeats but not the publication date.
- ABS rebasing restates earlier values: all history changes at once and the view follows,
  as Landing does.
- The US and Australian index levels use different bases and cannot be compared by value.
