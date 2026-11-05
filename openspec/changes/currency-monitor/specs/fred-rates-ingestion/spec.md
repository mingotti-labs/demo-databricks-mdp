## MODIFIED Requirements

### Requirement: Series fetched
Each run SHALL fetch every series named in `src/common/fred_series.py`
(`DGS10`, the US 10-year Treasury yield; `DFF`, the effective federal funds
rate; `DFEDTARU` and `DFEDTARL`, the upper and lower limit of the federal funds
target range; `CPIAUCSL`, `CPIAUCNS` and `CPILFESL`, the US consumer price index
for all urban consumers: all items seasonally adjusted, all items not seasonally
adjusted, and all items less food and energy seasonally adjusted; the daily exchange rates `DEXUSEU`,
`DEXJPUS`, `DEXUSUK`, `DEXSZUS`, `DEXCAUS`, `DEXSDUS`, `DEXUSAL`, `DEXUSNZ` and `DEXCHUS`; the ECB deposit
facility rate `ECBDFR`; the OECD short-term rates `IRSTCI01GBM156N`, `IR3TIB01JPM156N`, `IR3TIB01CAM156N`,
`IR3TIB01CHM156N`, `IR3TIB01SEM156N`, `IR3TIB01NZM156N`, `IR3TIB01CNM156N`; and the OECD long-term rates
`IRLTLT01EZM156N`, `IRLTLT01JPM156N`, `IRLTLT01GBM156N`, `IRLTLT01CHM156N`, `IRLTLT01CAM156N`, `IRLTLT01SEM156N`,
`IRLTLT01NZM156N`) from the FRED
API at the address in the bundle variable `fred_api_url`, using the key in secret
`api_key` of scope `fred`. For each it SHALL read the series' title, units and
frequency and its observations.

#### Scenario: The 10-year yield is fetched
- **WHEN** `run_fred` runs
- **THEN** rows exist for `series_id` `DGS10` with `title` "Market Yield on U.S.
  Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment
  Basis", `units` `Percent` and `frequency` `Daily`

#### Scenario: The Fed's policy rate is fetched
- **WHEN** `run_fred` runs
- **THEN** rows exist for `series_id` `DFEDTARU` and `DFEDTARL` (daily since
  2008-12-16) and `DFF`, each with its own `title`

#### Scenario: Consumer prices are fetched
- **WHEN** `run_fred` runs
- **THEN** rows exist for `series_id` `CPIAUCSL` (since 1947-01-01), `CPIAUCNS`
  (since 1913-01-01) and `CPILFESL` (since 1957-01-01), each with `frequency`
  `Monthly` and every `observation_date` on the first day of a month

#### Scenario: A series is added to the list
- **WHEN** a series named in `fred_series.py` has no stored rows
- **THEN** the run requests all its observations, and the other series stay
  incremental

#### Scenario: A request fails
- **WHEN** FRED answers a request with an error status
- **THEN** the fetch task fails with the status and FRED's message, writes no
  file for that run, and neither the key nor a URL containing it is logged

#### Scenario: A new series loads its whole history
- **WHEN** `run_fred` runs for the first time after `DEXSZUS` is added
- **THEN** rows exist for `DEXSZUS` from 1971-01-04
