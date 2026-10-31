# FRED (St. Louis Fed)

Economic time series through a free REST API (`api.stlouisfed.org/fred`). Needs a
free API key, kept in secret scope `fred`, key `api_key` (iac `secret-scopes`; the
CI/CD service principal has READ). Rate limit: 120 requests a minute.

- URL: bundle variable `fred_api_url`, same for every target.
- Code: `src/common/fred_series.py` (request helper, rows), `src/common/fetch_fred.py`
  (first task of `run_fred`), `src/layers/bronze/fred/`,
  `src/layers/bronze/fred_publish/`, `src/layers/silver/landing/fred/`.
- The key travels in the query string, and `requests` puts the whole URL into its
  exceptions, so `get_json` re-raises every failure as a `RuntimeError` with the
  path, series and HTTP status only; a unit test proves the key is not in the
  message or the traceback.

## Series fetched

| Series | What it is | From | Frequency |
|---|---|---|---|
| `DGS10` | market yield on 10-year US Treasuries (set by trading, not a policy rate) | 1962-01-02 | daily, weekdays |
| `DFF` | effective federal funds rate (banks' overnight lending) | 1954-07-01 | daily, 7 days |
| `DFEDTARU` | Fed target range, upper limit (the counterpart of the RBA cash rate target) | 2008-12-16 | daily, 7 days |
| `DFEDTARL` | Fed target range, lower limit | 2008-12-16 | daily, 7 days |

Not fetched: `FEDFUNDS`, the monthly average of `DFF`. Add a series by naming it in
`SERIES` in `fred_series.py`.

## Shape and gotchas

- `series/observations` returns `{date, value}` rows (plus `realtime_start` and
  `realtime_end`, which echo the request day and are not kept). One call returns up
  to 100,000 rows; `DGS10` is 16,913. `value` is text; `.` means no value (721 days
  for `DGS10`, market holidays) and is skipped.
- `series` returns the title, units and frequency, kept on every row.
- An unknown series is HTTP 400 with an `error_message` in JSON.
- All series share one long table (`observations`, told apart by `series_id`).
  After the first run only the 31 days before a series' last stored date are
  requested (`observation_start`); `reload=true` requests everything.
- First load: 55,667 rows. A later run writes about 120 rows.
- Landing turns `observation_date` into a date; Bronze keeps `yyyy-MM-dd` text.
