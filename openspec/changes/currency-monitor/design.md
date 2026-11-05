## Context

- FRED source: `src/common/fred_series.py` lists the series; a series with nothing stored loads its full history.
  `market_rate_daily` maps source series to `rate_code` through `RATES` in `src/common/investments.py`
  (code, name, source, series id, unit). Landing has RBA `FCMYGBAG10D` (Australian 10-year, daily from 2013) unmapped.
- `market_rate_indicator_daily` (`inflation-deflation-monitor`): per series and `^GSPC` trading day, the latest value on or
  before the day, its 200-day average and the average's 20-row change; query in `src/common/inflation_sql.py`.
- A new Yahoo benchmark loads all its history (`plan()`); `price_indicator_daily` gives every listing a 200-day average.
- Probe P0 (`references/poc/currency-monitor/p0_fred_series.txt`, public FRED CSV, 2026-11-05): every series below exists;
  first and last dates are listed there.

## Goals / Non-Goals

**Goals:** for each main currency, is it gaining or losing against USD and against AUD; is the dollar in a rising
megatrend; what each country pays, short and long; one reusable way to add a currency or a base.

**Non-Goals:** a rating or advice, the Big Mac index, BIS policy rates, intraday or forward rates, CD rates of banks.

## Decisions

### D1. Series (all FRED unless noted)

| Currency | Exchange rate (daily H.10) | Short-term rate | 10-year yield |
|---|---|---|---|
| USD | (base) | `DFF` (loaded) | `DGS10` (loaded) |
| AUD | `DEXUSAL` USD per AUD | RBA `FIRMMCRTD` (loaded) | RBA `FCMYGBAG10D` (Landing, to map) |
| EUR | `DEXUSEU` USD per EUR | `ECBDFR` daily | `IRLTLT01EZM156N` monthly |
| JPY | `DEXJPUS` JPY per USD | `IR3TIB01JPM156N` 3-month, monthly | `IRLTLT01JPM156N` monthly |
| GBP | `DEXUSUK` USD per GBP | `IRSTCI01GBM156N` call money, monthly (its 3-month stops 2026-01) | `IRLTLT01GBM156N` monthly |
| CHF | `DEXSZUS` CHF per USD | `IR3TIB01CHM156N` 3-month, monthly | `IRLTLT01CHM156N` monthly |
| SEK | `DEXSDUS` SEK per USD | `IR3TIB01SEM156N` 3-month, monthly | `IRLTLT01SEM156N` monthly |
| CAD | `DEXCAUS` CAD per USD | `IR3TIB01CAM156N` 3-month, monthly | `IRLTLT01CAM156N` monthly |
| NZD | `DEXUSNZ` USD per NZD | `IR3TIB01NZM156N` 3-month, monthly | `IRLTLT01NZM156N` monthly |
| CNY | `DEXCHUS` CNY per USD | `IR3TIB01CNM156N` 3-month, monthly | none on FRED |

The AUD rate comes from FRED (`DEXUSAL`, from 1971) rather than the RBA series already mapped (from 2023), so every
currency has the same source and history. Per country the short-term rate is the freshest OECD series on FRED (probe P0): the 3-month interbank rate where it is
current (close to what a 3-month CD pays), the UK's call money rate (its 3-month stops 2026-01); the euro uses the ECB
deposit rate (daily). These are market rates, close to but not the policy rate; `rate_name` and the dashboard say which. The US Dollar Index is Yahoo `DX-Y.NYB` (ICE, six currencies with fixed weights, from 1971): the megatrend. The Federal
Reserve's Nominal Broad U.S. Dollar Index (FRED `DTWEXBGS`, about 26 currencies weighted by trade with the US, daily from
2006) is added as context (`rate_code` `us_dollar_broad_index`, in `market_rate_daily` and, with its 200-day average, in
`market_rate_indicator_daily`). When the two disagree, the dollar moves differently against Europe than against the rest.

### D2. One currency list drives the cross rates
`src/common/currency.py` holds `CURRENCIES`: code, name, the exchange-rate `rate_code`, its quote (`usd_per_unit` or
`units_per_usd`), the short-term and the 10-year `rate_code`. `currency_value_sql()` turns each exchange rate into the
value of one unit in USD (`usd_per_unit` as is, `units_per_usd` as 1 / rate); the value in AUD is that value divided by
the value of one AUD in USD, on the same day. `BASES = ["USD", "AUD"]`: another base is one entry. A new currency is one
row in `CURRENCIES`, one FRED series and one `RATES` row.

### D3. Silver series in `market_rate_indicator_daily`
New series per currency and base: `currency_value_<code>_in_<base>` (for example `currency_value_chf_in_aud`), unit
`<base>_per_unit`, `is_calculated` true. Rising means the currency gains against the base. The monthly and daily interest
rates are carried there like the others (`observation_date` keeps each reading's date). `inflation_sql.py`'s query becomes
generic over a list of series (renamed `market_rate_indicator_sql.py`), so the inflation and currency series share one
query; the inflation rows must not change (checked before deploy).

### D4. Monitor rows
`monitor_code` `currency`, `monitor_name` "Currency Monitor". Lens `us_dollar` ("Against the US dollar"): signal
`dollar_index` (is_yes = the US Dollar Index is above its 200-day average: the dollar is strong; band red below, green above
with a rising average, else yellow), signal `dollar_broad_index` (the same rule on the broad index, context: not in the
summary count) and one signal per other currency (`eur`, `jpy`, ...: is_yes = its value in USD is
above its 200-day average, it gains against the dollar; same bands). Lens `australian_dollar` ("Against the Australian
dollar"): one signal per currency other than AUD, USD included. `measured_value` the value, `threshold_value` the average,
`reason_text` a sentence. A `summary` row per lens: `yes_count` currencies gaining, `action_name` "N of 9 gaining".
A currency counts on a day when its value is at most 10 days old (FRED's exchange rates arrive weekly). Query
`src/common/currency_signals_sql.py`; `monitor_daily_signal` becomes the union of three monitors.

### D5. Dashboard "Currency Monitor" and the agent
Generated by `cicd/build_dashboards.py` (`common/currency_queries.py`, `common/currency_dashboard.py`). Page "Currency
Monitor": intro bullets; two circles (the US Dollar Index and the broad index, each strong or weak, with the index and
its average on hover); a currency grid (rows the nine currencies,
columns against USD and against AUD, coloured gaining or losing); distance from the average for each currency against USD
and against AUD (bars); the two dollar indexes with their averages over the shared 36-month axis; the rates table (currency, short-term
rate and date, 10-year yield and date, a mark when older than 3 months). Page "Currency Deep Dive": currency selector; its
value in USD and in AUD with averages; its short-term rate and its 10-year yield over time (the 10-year line only
when the country has one: none for China). Agent: examples from these queries,
instructions (the cross-rate rule, gaining means above the average, the stale rates), three benchmarks.

## Probes

- **P0** done (FRED series exist, dates above).
- **P1**: dev runs `fred` (new series, full history), `portfolio` and `yahoo` (`DX-Y.NYB` loads from 1971), then `investments`.
- **P2** before deploy: CHF in AUD on one day equals (USD per AUD) / (CHF per USD) by hand; the inflation rows of
  `market_rate_indicator_daily` and `monitor_daily_signal` unchanged (EXCEPT both ways).
- **P3** before deploy on dev history: the dollar strong share per year, and a known episode (the dollar strong in 2022).
- **P4**: dashboard and agent queries in dev; benchmark evaluation; the user's check.

## Risks / Trade-offs

- [Stale OECD rates (the euro 10-year, and any series that stops later)] → shown with their reading date and marked when
  older than 3 months; another OECD series or BIS later if needed.
- [Yahoo `DX-Y.NYB` gaps or a renamed symbol] → P1 checks it; FRED `DTWEXBGS` is the fallback.
- [Refactoring the shared indicator query changes the inflation series] → P2 compares them before deploy.
- [Deploy order: the agent lists no new table] → no deadlock (the tables exist; only rows are new).

## Migration Plan

Dev: draft PR deploy, P1 runs (one at a time), `run_investments verify=true`. Prd: the merge deploys; CI runs `fred`,
`portfolio`, `yahoo`, `investments` (alphabetical; `investments` before `portfolio` and `yahoo`, so the dollar index
appears in prd after one more `investments` run: the user starts it, or the next scheduled run).
