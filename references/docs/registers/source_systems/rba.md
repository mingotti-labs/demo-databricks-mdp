# Reserve Bank of Australia (RBA)

Statistical tables published as free CSV files at fixed addresses: exchange
rates, the cash rate (the RBA's base rate, which mortgage rates and bond yields
follow), government bond yields and lending rates. No key.

- URL: `www.rba.gov.au/statistics/tables/csv/<file>`, bundle variable
  `rba_tables_url` (the folder itself returns 403: the server does not list it;
  every file returns 200). Index of tables: `www.rba.gov.au/statistics/tables/`.
- Auth: none. The fetch sends the `http_user_agent` contact string.
- Code: `src/common/rba_tables.py` (parser), `src/common/fetch_rba.py` (first
  task of `run_rba`), `src/layers/bronze/rba/`, `src/layers/bronze/rba_publish/`,
  `src/layers/silver/landing/rba/`.

## Tables fetched

| Table | File | Content | Series | From | Frequency |
|---|---|---|---|---|---|
| F11.1 | `f11.1-data.csv` | exchange rates (AUD/USD is `FXRUSD`) | 23 (21 with data) | 03-Jan-2023 | daily |
| F1 | `f1-data.csv` | money market rates, cash rate target `FIRMMCRTD` | 17 | 04-Jan-2011 | daily |
| F2 | `f2-data.csv` | government bond yields, 10 year is `FCMYGBAG10D` | 5 | 20-May-2013 | daily |
| F5 | `f5-data.csv` | indicator lending rates, standard variable owner-occupier mortgage is `FILRHLBVS` | 30 | 31-Jan-1959 | monthly |

Not fetched: exchange rates before 2023 (Excel files `f11hist.xls`,
`f11hist-1969-2009.xls`), F6 (rates on outstanding housing loans; dates written
as `dd/mm/yyyy`, from 2019), the monthly copies F2.1 and F1.1.

## Shape and gotchas

- One column per series; a block of header rows (title, description,
  frequency, type, units, source, publication date) ending in `Series ID`, then
  one row per date written `dd-Mon-yyyy`. The file starts with a byte order
  mark and has blank lines between header rows.
- The parser turns it into one row per series and date, empty cells skipped;
  values and dates stay text in Bronze; Landing turns `observation_date` and
  `publication_date` into dates. All four tables share one long table
  (`observations`), told apart by `table_id`, to save table-quota slots.
- Recent dates are filled in late: F1's latest dates leave most cells empty,
  and F11.1's AED and ZAR series stopped in 2024. So after the first run only
  the 31 days before a table's last stored date are written; `reload=true`
  writes everything.
- First load: 89,962 rows, 73 series. A later run writes about 850 rows.
- Local downloads on this Windows machine: use `curl.exe` from System32; the
  Git Bash curl fails on the corporate proxy's self-signed certificate.
