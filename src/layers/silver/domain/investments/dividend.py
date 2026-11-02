# Silver Domain investments: dividend (openspec silver-domain-investments). Yahoo
# dividends with the Australian dollar amount (RBA rate of the latest date on or before
# the ex-date), the pay date (Yahoo's, else the ex-date plus the settings offset) and a
# flag for one-off amounts.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.investments import SPECIAL_DIVIDEND_FACTOR, SPECIAL_DIVIDEND_LOOKBACK  # noqa: E402

LANDING = "silver_landing"


@dp.materialized_view(
    comment="One row per listing and ex-date. dividend_amount_in_australian_dollars uses the RBA "
    "rate of the latest date on or before the ex-date; is_special marks an amount over twice the "
    "median of the previous four."
)
def dividend():
    return spark.sql(
        f"""
        WITH dividends AS (
          SELECT l.listing_id, e.symbol AS trading_symbol_code, to_date(e.date) AS ex_dividend_date,
                 CAST(e.value AS DECIMAL(18, 6)) AS dividend_amount, l.currency_code,
                 e.ingested_timestamp
          FROM {LANDING}.yahoo__events e
          JOIN listing l ON l.trading_symbol_code = e.symbol
          WHERE e.event_type = 'dividend'
        ), with_previous AS (
          SELECT *,
                 array_sort(collect_list(dividend_amount) OVER (
                   PARTITION BY listing_id ORDER BY ex_dividend_date
                   ROWS BETWEEN {SPECIAL_DIVIDEND_LOOKBACK} PRECEDING AND 1 PRECEDING
                 )) AS previous_amounts
          FROM dividends
        ), pay_dates AS (
          SELECT symbol, to_date(ex_dividend_date) AS ex_dividend_date, to_date(dividend_date) AS pay_date,
                 row_number() OVER (
                   PARTITION BY symbol, ex_dividend_date ORDER BY scd_valid_from_timestamp DESC
                 ) AS version_rank
          FROM {LANDING}.yahoo__calendar
          WHERE ex_dividend_date IS NOT NULL AND dividend_date IS NOT NULL
        ), exchange_rates AS (
          SELECT observation_date, rate FROM (
            SELECT observation_date, try_cast(value AS DECIMAL(18, 6)) AS rate
            FROM {LANDING}.rba__observations WHERE series_id = 'FXRUSD'
          ) WHERE rate IS NOT NULL
        ), converted AS (
          SELECT d.*, r.rate,
                 row_number() OVER (
                   PARTITION BY d.listing_id, d.ex_dividend_date ORDER BY r.observation_date DESC
                 ) AS rate_rank
          FROM with_previous d
          LEFT JOIN exchange_rates r ON r.observation_date <= d.ex_dividend_date
        ), settings AS (
          SELECT CAST(value AS INT) AS pay_date_offset_days
          FROM {LANDING}.portfolio__settings
          WHERE is_current AND setting = 'pay_date_offset_days'
        )
        SELECT c.listing_id,
               c.trading_symbol_code,
               c.ex_dividend_date,
               c.dividend_amount,
               c.currency_code,
               CAST(c.dividend_amount / c.rate AS DECIMAL(18, 6)) AS dividend_amount_in_australian_dollars,
               coalesce(p.pay_date, date_add(c.ex_dividend_date, s.pay_date_offset_days)) AS pay_date,
               p.pay_date IS NULL AS pay_date_is_estimated,
               CASE WHEN size(c.previous_amounts) = 0 THEN false
                    WHEN size(c.previous_amounts) % 2 = 1
                    THEN c.dividend_amount > {SPECIAL_DIVIDEND_FACTOR}
                                    * c.previous_amounts[size(c.previous_amounts) DIV 2]
                    ELSE c.dividend_amount > {SPECIAL_DIVIDEND_FACTOR}
                                    * ((c.previous_amounts[size(c.previous_amounts) DIV 2 - 1]
                                        + c.previous_amounts[size(c.previous_amounts) DIV 2]) / 2)
               END AS is_special,
               c.ingested_timestamp
        FROM converted c
        CROSS JOIN settings s
        LEFT JOIN pay_dates p
          ON p.symbol = c.trading_symbol_code
         AND p.ex_dividend_date = c.ex_dividend_date
         AND p.version_rank = 1
        WHERE c.rate_rank = 1
        """
    )
