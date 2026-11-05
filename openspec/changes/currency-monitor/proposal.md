## Why

Story "Value of the dollar" (planning `references/user-stories/monitor-track-the-value-of-the-dollar.md`), renamed the
**Currency Monitor** by the user (2026-11-05) and built in parts. Part 1, this change: the individual investor wants to see
whether other main currencies are gaining or losing value against the US dollar (the world's main currency) and against
the Australian dollar (the investor's base currency), whether the dollar itself is in a rising or falling megatrend, and
what each country pays in interest. That picture comes before any decision to hold some capital in another currency as CDs
(the strategy is a later part, with the Big Mac index).

## What Changes

- **Data, all from existing sources, no new table**:
  - nine exchange rates from FRED's daily H.10 series (euro, yen, pound, Swiss franc, Canadian dollar, Swedish krona,
    Australian dollar, New Zealand dollar, yuan, each against the US dollar), added to the FRED fetch and to
    `market_rate_daily`; the six currencies of the US Dollar Index (EUR, JPY, GBP, CAD, SEK, CHF) are all included;
  - the US Dollar Index (`DX-Y.NYB`, ICE, six currencies) as a Yahoo benchmark row in `data/portfolio/benchmarks.csv`, so
    `price_daily` and `price_indicator_daily` carry it with its 200-day average; and, for context, the Federal Reserve's
    Nominal Broad U.S. Dollar Index (`DTWEXBGS`, about 26 currencies weighted by trade, daily from 2006) from FRED;
  - short-term interest rates: the ECB deposit facility rate (`ECBDFR`, daily), the OECD 3-month interbank rates of Japan,
    Canada, Switzerland, Sweden, New Zealand and China and the OECD call money rate of the UK (monthly, on FRED; the
    freshest series per country, and a 3-month rate is close to what a CD pays), next to the federal funds and RBA cash
    rates already loaded;
  - 10-year government bond yields: the OECD long-term rates of the euro area, Japan, the UK, Switzerland, Canada, Sweden
    and New Zealand (monthly, on FRED), next to the US 10-year (FRED, loaded) and the Australian 10-year (RBA `FCMYGBAG10D`, daily,
    already in Landing, newly mapped).
- **Reusable cross rates (silver)**: every exchange rate is turned into "the value of one unit of the currency in US
  dollars"; its value in Australian dollars is that divided by the value of one Australian dollar in US dollars. One list of
  currencies drives it, so adding a currency (or another base) is one entry. These series go into
  `market_rate_indicator_daily` (with their 200-day average and its 20-day change), as do the rates, carried from their
  latest reading.
- **The monitor (gold)**: rows of `monitor_daily_signal` with monitor `currency`: lens `us_dollar` (the dollar megatrend:
  the US Dollar Index against its 200-day average; the broad index the same way, as context, not counted; and each of the nine other currencies against the dollar) and lens
  `australian_dollar` (each of the nine others, the US dollar included, against the Australian dollar). A currency is
  gaining (`is_yes`) when its value in the base currency is above its 200-day average. A summary row per lens counts the
  currencies gaining. No rating or advice yet.
- **Dashboard "Currency Monitor"** (generated like the other two): first page "Currency Monitor" with two circles, the US Dollar Index and the broad index (each strong or weak),
  the currencies against USD and against AUD (gaining or losing, distance from the average) and the interest rate table (short-term
  and 10-year with the date of each reading); a "Currency Deep Dive" page with a currency selector (its value in USD and AUD
  with their averages, its short-term rate and its 10-year yield over time, the 10-year when the country has one).
- **Investment Intelligence agent**: the currency rows, rules, examples and benchmarks.
- **Verification**: one row per currency, base and day; a cross rate equals its two USD rates; the summary counts its rows.

## Decisions (user, 2026-11-05)

- Monitor name: Currency Monitor; built gradually; part 1 is the dollar megatrend, the currencies against USD and AUD,
  and the interest rates.
- Megatrend: the 200-day average, as the other monitors. The US Dollar Index (DXY) is the megatrend; the Fed's broad
  dollar index is added as context and shown as a second circle on the first page (user, 2026-11-05).
- Main currencies: USD, EUR, JPY, GBP, CHF, CAD, SEK, AUD, NZD, CNY (the six currencies of the US Dollar Index plus
  AUD, NZD and CNY; SEK added by the user after checking the index, 2026-11-05).
- The Currency Deep Dive page shows the 10-year yield when the country has one.
- Both a short-term rate and the 10-year yield per country, from FRED for now (the BIS daily policy rates are free but a new
  source, about 12 table slots; later, after a table clean-up, if the monthly figures are too slow).

## Capabilities

### New Capabilities
- `gold-currency-monitor`: the currency monitor rows, its dashboard and its part of the Genie agent.

### Modified Capabilities
- `silver-domain-investments`: more market rates (exchange rates and interest rates) and the currency values in
  `market_rate_indicator_daily`.
- `fred-rates-ingestion`: more FRED series.

## Impact

- Table slots: none (new rows in existing tables). Quota 486 of 500.
- Runs: `fred` (new series load their full history), `portfolio` and `yahoo` (the new benchmark), `investments`.
- Known gaps, shown on the dashboard with each reading's date: the euro area 10-year (last 2026-01) is stale on FRED;
  China has no 10-year on FRED. The short-term rates use the freshest OECD series per country (probe P0: the call money
  rates of Switzerland, New Zealand, China and Sweden stopped between 2020 and 2025, their 3-month rates are current). FRED's exchange rates arrive weekly, so the latest days can be up to about 10 days old.
- Not in this change: the Big Mac index, a rating or strategy, the BIS source.

## Cross-repo dependencies

None (FRED key and volumes exist; no new schema or table).
Planning repo: the story is renamed Currency Monitor and gets an Analysis section at archive.

## Model

Sonnet for implementation: each part repeats a pattern built in `inflation-deflation-monitor`.
