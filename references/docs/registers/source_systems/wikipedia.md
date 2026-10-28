# Wikipedia S&P 500 list

The `constituents` table of Wikipedia's "List of S&P 500 companies". Free, no
key. Chosen over FMP because FMP's free plan refuses the list (probe P4 in
`references/docs/registers/probes.md`).

- URL: `en.wikipedia.org/wiki/List_of_S%26P_500_companies`, bundle variable
  `wikipedia_sp500_url`, same for every target.
- Auth: none. Wikimedia asks for a contact `User-Agent`: bundle variable
  `http_user_agent`.
- License: CC BY-SA 4.0; the raw table's comment carries the attribution.
- Code: `src/common/wikipedia_sp500.py`,
  `src/layers/bronze/wikipedia/sp500_constituents_raw.py`,
  `src/layers/bronze/wikipedia_publish/sp500_constituents_scd2.py`,
  `src/layers/silver/landing/wikipedia/sp500_constituents.py`.

## Shape and gotchas

- Columns: symbol, security, GICS sector, GICS sub-industry, headquarters
  location, date added, CIK, founded. 503 rows, 503 symbols, 500 CIKs (share
  classes such as GOOGL/GOOG share a CIK).
- Everything stays text. CIK is zero-padded to 10 digits (read as a number it
  loses its zeros). Symbols keep dots (`BRK.B`); Yahoo uses dashes.
- `founded` is free text (`1928 (2011)`, `1904/1946/1959`).
- The page's "Selected changes" table is gone, so membership history comes only
  from our SCD2 versions, from the first load.
- The helper fails if the table or a column is missing, so a layout change
  stops the pipeline instead of loading wrong data.
- A ticker can point to a company with no filings yet: XOM now maps to
  ExxonMobil Holdings Corp (CIK 2115436); see the `portfolio` predecessor CIKs.
