"""SQL of the strategy events table (openspec strategy-events): setup starts, entries and setup ends of strategy 001
(bear market mutual fund, on the S&P 500) and strategy 002 (short selling, on the index members), one row per event.

Plain strings so a probe can run the exact query against dev or prd before it goes into a pipeline. `domain` is the silver
schema (with the catalog in a probe); `climate_source` is the table with the market climate rows (`monitor_daily_signal`)
and `member_source` the member valuation per day (`valuation_daily_index_member`), each a table or a parenthesised query.
"""

from common.market_climate import MONITOR_CODE as CLIMATE_MONITOR_CODE
from common.market_climate_sql import DOMAIN
from common.strategy import (
    BEAR_FUND_CODE,
    BEAR_FUND_NAME,
    DOWN_WEEKS_FOR_ENTRY,
    FIVE_WEEKS,
    HALF_BAND,
    HALF_DROP_RATIO,
    INDEX_SYMBOL,
    INTERIM_BAND,
    PRICE_TO_SALES_MIN,
    QUARTER_BAND,
    QUARTER_DROP_RATIO,
    SHORT_SELLING_CODE,
    SHORT_SELLING_NAME,
    events_values_sql,
)

# A week is complete when its last trading day is its Friday, or its Friday has passed (a holiday Friday).

def week_complete(alias: str = "") -> str:
    """The week of `alias` (a table with week_start and week_end_date) is complete."""
    prefix = f"{alias}." if alias else ""
    return f"({prefix}week_end_date = date_add({prefix}week_start, 4) OR current_date() > date_add({prefix}week_start, 4))"


STATE_COLUMNS = """strategy_code, trading_symbol_code, listing_id, week_start, week_end_date, week_close_amount,
           five_weeks_close_amount, week_change_ratio, price_to_sales_ratio, down_week_count, is_setup_on, ingested_timestamp"""


def strategy_events_query(domain: str = DOMAIN, climate_source: str = "monitor_daily_signal",
                          member_source: str = "valuation_daily_index_member") -> str:
    """Events of both strategies, evaluated on complete weeks that have a market climate row."""
    return f"""
    WITH strategies AS (
      SELECT * FROM VALUES ('{BEAR_FUND_CODE}', '{BEAR_FUND_NAME}'), ('{SHORT_SELLING_CODE}', '{SHORT_SELLING_NAME}')
        AS strategies(strategy_code, strategy_name)
    ), event_names AS (
      SELECT * FROM VALUES {events_values_sql()} AS event_names(event_code, event_name)
    ), red AS (
      SELECT signal_date, max(CAST(band_code = 'red' AS INT)) = 1 AS is_red
      FROM {climate_source}
      WHERE monitor_code = '{CLIMATE_MONITOR_CODE}' AND signal_code = 'climate'
      GROUP BY signal_date
    ), index_days AS (
      SELECT listing_id, trading_symbol_code, price_date, price_close, ingested_timestamp
      FROM {domain}.price_daily WHERE trading_symbol_code = '{INDEX_SYMBOL}'
    ), index_weeks AS (
      SELECT max(listing_id) AS listing_id, max(trading_symbol_code) AS trading_symbol_code,
             CAST(date_trunc('WEEK', price_date) AS DATE) AS week_start, max(price_date) AS week_end_date,
             max_by(price_close, price_date) AS week_close, min(ingested_timestamp) AS ingested_timestamp
      FROM index_days GROUP BY CAST(date_trunc('WEEK', price_date) AS DATE)
    ), bear_weeks AS (
      SELECT w.*, lag(week_close, 1) OVER (ORDER BY week_start) AS previous_close,
             lag(week_close, {FIVE_WEEKS}) OVER (ORDER BY week_start) AS five_weeks_close
      FROM index_weeks w
    ), bear_states AS (
      SELECT '{BEAR_FUND_CODE}' AS strategy_code, trading_symbol_code, listing_id, week_start, week_end_date,
             CAST(week_close AS DECIMAL(18, 6)) AS week_close_amount,
             CAST(five_weeks_close AS DECIMAL(18, 6)) AS five_weeks_close_amount,
             CAST(week_close / previous_close - 1 AS DECIMAL(18, 10)) AS week_change_ratio,
             CAST(NULL AS DECIMAL(18, 4)) AS price_to_sales_ratio, CAST(NULL AS INT) AS down_week_count,
             r.is_red AND week_close < five_weeks_close AS is_setup_on, w.ingested_timestamp
      FROM bear_weeks w JOIN red r ON r.signal_date = w.week_end_date
      WHERE {week_complete('w')}
    ), stock_weeks AS (
      SELECT p.listing_id, max(p.trading_symbol_code) AS trading_symbol_code,
             CAST(date_trunc('WEEK', p.price_date) AS DATE) AS week_start,
             max_by(p.price_close_adjusted, p.price_date) AS week_close, min(p.ingested_timestamp) AS ingested_timestamp
      FROM {domain}.price_daily p
      JOIN (SELECT DISTINCT listing_id FROM {member_source}) m ON m.listing_id = p.listing_id
      WHERE p.price_date >= (SELECT date_sub(min(signal_date), 70) FROM red)
      GROUP BY p.listing_id, CAST(date_trunc('WEEK', p.price_date) AS DATE)
    ), stock_down AS (
      SELECT *, coalesce(CAST(week_close < lag(week_close) OVER (PARTITION BY listing_id ORDER BY week_start) AS INT), 0)
               AS is_down
      FROM stock_weeks
    ), stock_run AS (
      SELECT *, sum(1 - is_down) OVER (PARTITION BY listing_id ORDER BY week_start) AS run_group FROM stock_down
    ), stock_streak AS (
      SELECT *, sum(is_down) OVER (PARTITION BY listing_id, run_group ORDER BY week_start) AS down_weeks,
             lag(week_close) OVER (PARTITION BY listing_id ORDER BY week_start) AS previous_close
      FROM stock_run
    ), short_states AS (
      SELECT '{SHORT_SELLING_CODE}' AS strategy_code, s.trading_symbol_code, s.listing_id, s.week_start, w.week_end_date,
             CAST(s.week_close AS DECIMAL(18, 6)) AS week_close_amount,
             CAST(NULL AS DECIMAL(18, 6)) AS five_weeks_close_amount,
             CAST(s.week_close / s.previous_close - 1 AS DECIMAL(18, 10)) AS week_change_ratio,
             m.price_to_sales_ratio, CAST(s.down_weeks AS INT) AS down_week_count,
             r.is_red AND m.price_to_sales_ratio > {PRICE_TO_SALES_MIN} AS is_setup_on, s.ingested_timestamp
      FROM stock_streak s
      JOIN index_weeks w ON w.week_start = s.week_start
      JOIN red r ON r.signal_date = w.week_end_date
      JOIN {member_source} m ON m.listing_id = s.listing_id AND m.valuation_date = w.week_end_date
      WHERE {week_complete('w')}
    ), states AS (
      SELECT {STATE_COLUMNS} FROM bear_states
      UNION ALL SELECT {STATE_COLUMNS} FROM short_states
    ), flagged AS (
      SELECT *, coalesce(is_setup_on, false) AS is_on,
             coalesce(lag(is_setup_on) OVER (PARTITION BY strategy_code, listing_id ORDER BY week_start), false) AS was_on
      FROM states
    ), periods AS (
      SELECT *, max(CASE WHEN is_on AND NOT was_on THEN week_end_date END)
                  OVER (PARTITION BY strategy_code, listing_id ORDER BY week_start
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS setup_start_date
      FROM flagged
    ), interim AS (
      SELECT p.strategy_code, p.listing_id, p.week_end_date, min(d.price_date) AS event_date
      FROM periods p
      JOIN index_days d ON d.price_date BETWEEN date_add(p.week_start, 7) AND date_add(p.week_start, 9)
       AND d.price_close / p.week_close_amount - 1 <= {QUARTER_DROP_RATIO}
      WHERE p.strategy_code = '{BEAR_FUND_CODE}' AND p.is_on
        AND p.week_change_ratio < 0 AND p.week_change_ratio > {QUARTER_DROP_RATIO}
      GROUP BY p.strategy_code, p.listing_id, p.week_end_date
    ), entries AS (
      SELECT strategy_code, listing_id, week_end_date, week_end_date AS event_date,
             CASE WHEN week_change_ratio <= {HALF_DROP_RATIO} THEN '{HALF_BAND}' ELSE '{QUARTER_BAND}' END AS entry_band_code
      FROM periods
      WHERE strategy_code = '{BEAR_FUND_CODE}' AND is_on AND week_change_ratio <= {QUARTER_DROP_RATIO}
      UNION ALL
      SELECT strategy_code, listing_id, week_end_date, event_date, '{INTERIM_BAND}' AS entry_band_code FROM interim
      UNION ALL
      SELECT strategy_code, listing_id, week_end_date, week_end_date AS event_date, CAST(NULL AS STRING)
      FROM periods WHERE strategy_code = '{SHORT_SELLING_CODE}' AND is_on AND down_week_count = {DOWN_WEEKS_FOR_ENTRY}
    ), events AS (
      SELECT strategy_code, trading_symbol_code, listing_id, week_end_date AS event_date, 'setup_start' AS event_code,
             setup_start_date, CAST(NULL AS STRING) AS entry_band_code, week_close_amount, five_weeks_close_amount,
             week_change_ratio, price_to_sales_ratio, down_week_count, ingested_timestamp
      FROM periods WHERE is_on AND NOT was_on
      UNION ALL
      SELECT strategy_code, trading_symbol_code, listing_id, week_end_date, 'setup_end', setup_start_date,
             CAST(NULL AS STRING), week_close_amount, five_weeks_close_amount, week_change_ratio, price_to_sales_ratio,
             down_week_count, ingested_timestamp
      FROM periods WHERE NOT is_on AND was_on
      UNION ALL
      SELECT p.strategy_code, p.trading_symbol_code, p.listing_id, e.event_date, 'entry', p.setup_start_date,
             e.entry_band_code, p.week_close_amount, p.five_weeks_close_amount, p.week_change_ratio,
             p.price_to_sales_ratio, p.down_week_count, p.ingested_timestamp
      FROM entries e
      JOIN periods p ON p.strategy_code = e.strategy_code AND p.listing_id = e.listing_id AND p.week_end_date = e.week_end_date
    ), numbered AS (
      SELECT *, CASE WHEN event_code = 'entry' THEN
                  row_number() OVER (PARTITION BY strategy_code, listing_id, setup_start_date, event_code ORDER BY event_date)
                END AS entry_number
      FROM events
    )
    SELECT n.strategy_code, s.strategy_name, n.trading_symbol_code, n.event_date, n.event_code, e.event_name,
           n.listing_id, n.setup_start_date, n.entry_number, n.entry_number = 1 AS is_first_entry, n.entry_band_code,
           n.week_close_amount, n.five_weeks_close_amount, n.week_change_ratio, n.price_to_sales_ratio, n.down_week_count,
           {reason_text_sql()} AS reason_text, 'USD' AS currency_code, n.ingested_timestamp
    FROM numbered n
    JOIN strategies s ON s.strategy_code = n.strategy_code
    JOIN event_names e ON e.event_code = n.event_code
    """


def reason_text_sql() -> str:
    """One plain sentence per strategy and event."""
    bear = f"n.strategy_code = '{BEAR_FUND_CODE}'"
    change = "round(abs(n.week_change_ratio) * 100, 1)"
    return f"""CASE
        WHEN {bear} AND n.event_code = 'setup_start' THEN concat('A market climate light is red and the S&P 500 closed the week at ',
          round(n.week_close_amount, 2), ', below ', round(n.five_weeks_close_amount, 2), ' five weeks earlier.')
        WHEN {bear} AND n.event_code = 'setup_end' THEN concat('No climate light is red, or the S&P 500 closed the week at ',
          round(n.week_close_amount, 2), ' at or above its close five weeks earlier (', round(n.five_weeks_close_amount, 2), ').')
        WHEN {bear} AND n.entry_band_code = '{INTERIM_BAND}' THEN concat('A day in the week after a small fall (',
          {change}, '%) closed at least 2.5% below that week close of ', round(n.week_close_amount, 2),
          ': invest a quarter of equity in the bear fund.')
        WHEN {bear} THEN concat('The S&P 500 fell ', {change}, '% on the week: invest ',
          CASE WHEN n.entry_band_code = '{HALF_BAND}' THEN 'half' ELSE 'a quarter' END, ' of equity in the bear fund on Monday.')
        WHEN n.event_code = 'setup_start' THEN concat('A market climate light is red and price-to-sales is ',
          round(n.price_to_sales_ratio, 1), ', above {PRICE_TO_SALES_MIN}.')
        WHEN n.event_code = 'setup_end' THEN 'No climate light is red, or price-to-sales is no longer above {PRICE_TO_SALES_MIN}.'
        ELSE concat('The stock closed its ', n.down_week_count, 'th week in a row down while the setup is on.')
      END"""
