"""Dataset queries of the Strategy Monitor dashboard (openspec strategy-monitor-dashboard).

Bare gold table names: the dashboard's dataset catalog and schema (`gold_analytics_gateway` of the target's catalog) fill
them in; silver tables carry their schema name. `:as_of_date` is a dashboard date parameter (default today); the week shown
is the latest complete week on or before it. `:fund_code` is the Bear Fund Deep Dive selector, `:setup_period` the past
setup period chosen on the Bear Market Fund page and `:history_range_code` the history range of the deep dive. The weekly
states are the same query the events table is built from. Also the example SQL of the Genie agent.
"""

from common.market_climate_queries import HISTORY_DATES, HISTORY_START
from common.strategy import (
    BEAR_FUND_CODE,
    EFFICIENCY_MIN,
    EFFICIENT_VOLUME_MIN,
    FIVE_WEEKS,
    HALF_DROP_RATIO,
    QUARTER_DROP_RATIO,
    SHORT_SELLING_CODE,
)
from common.strategy_events_sql import strategy_states_query

DATASETS: dict[str, tuple[str, str]] = {}
SILVER = "silver_domain_investments"
STATES = f"states AS ({strategy_states_query(SILVER, 'monitor_daily_signal', 'valuation_daily_index_member')})"
AS_OF_DATE = "coalesce(:as_of_date, DATE '9999-12-31')"
BEAR = (
    f"bear AS (SELECT * FROM states WHERE strategy_code = '{BEAR_FUND_CODE}' AND week_end_date <= {AS_OF_DATE} "
    "ORDER BY week_end_date DESC LIMIT 1)"
)
SHORT_WEEK = (
    f"short_week AS (SELECT max(week_end_date) AS day FROM states WHERE strategy_code = '{SHORT_SELLING_CODE}' "
    f"AND week_end_date <= {AS_OF_DATE})"
)
EFFICIENT_DAY = (
    f"screen_day AS (SELECT max(price_date) AS day FROM {SILVER}.price_daily "
    f"WHERE trading_symbol_code = '^GSPC' AND price_date <= {AS_OF_DATE})"
)
EFFICIENT_SCREEN = f"""screen AS (
  SELECT l.trading_symbol_code, c.company_name, p.price_date, p.efficiency_tr60_ratio, p.efficiency_r60_ratio,
    p.close_sixty_day_change_ratio, p.price_range_sixty_day_average_ratio, p.true_range_sixty_day_average_ratio,
    p.volume_sixty_day_average_count,
    p.efficiency_tr60_ratio >= {EFFICIENCY_MIN} AS is_efficient,
    coalesce(p.volume_sixty_day_average_count > {EFFICIENT_VOLUME_MIN}, false) AS is_liquid
  FROM valuation_daily_index_member m
  JOIN {SILVER}.price_indicator_daily p ON p.listing_id = m.listing_id AND p.price_date = m.valuation_date
  LEFT JOIN {SILVER}.listing l ON l.listing_id = m.listing_id
  LEFT JOIN {SILVER}.company c ON c.company_id = m.company_id
  WHERE m.valuation_date = (SELECT day FROM screen_day) AND p.efficiency_tr60_ratio IS NOT NULL)"""
FUNDS = [
    ("SQQQ", "ProShares UltraPro Short QQQ", "3x short Nasdaq-100"),
    ("PSQ", "ProShares Short QQQ", "1x short Nasdaq-100"),
    ("SH", "ProShares Short S&P500", "1x short S&P 500"),
    ("SDS", "ProShares UltraShort S&P500", "2x short S&P 500"),
    ("SPXU", "ProShares UltraPro Short S&P500", "3x short S&P 500"),
]
FUND_VALUES = ", ".join(f"('{code}', '{name}', '{kind}', {order})" for order, (code, name, kind) in enumerate(FUNDS, 1))
FUND_ROWS = f"funds AS (SELECT * FROM VALUES {FUND_VALUES} AS funds(fund_code, fund_name, fund_description, fund_order))"


def dataset(name: str, title: str, query: str) -> None:
    DATASETS[name] = (title, " ".join(query.split()) + " ")


dataset("ds_strategy_freshness", "Data dates", f"""
WITH {STATES}, {BEAR}, {SHORT_WEEK}
SELECT (SELECT week_end_date FROM bear) AS bear_week_date, (SELECT day FROM short_week) AS short_week_date,
  (SELECT max(signal_date) FROM monitor_daily_signal WHERE monitor_code = 'market_climate' AND signal_code = 'climate') AS climate_date,
  (SELECT max(price_date) FROM {SILVER}.price_daily WHERE trading_symbol_code = '^GSPC') AS sp500_price_date,
  (SELECT max(event_date) FROM strategy_daily_event) AS latest_event_date
""")

dataset("ds_bear_week", "Strategy 001 setup and entry of the week", f"""
WITH {STATES}, {BEAR}
SELECT week_end_date, week_close_amount, five_weeks_close_amount, week_change_ratio, is_red,
  week_close_amount < five_weeks_close_amount AS is_lower_than_five_weeks, is_setup_on,
  CASE WHEN is_setup_on THEN 'GO' ELSE 'NO GO' END AS setup_text,
  CASE WHEN is_setup_on THEN 'green' ELSE 'red' END AS setup_light,
  CASE WHEN NOT is_setup_on THEN NULL
       WHEN week_change_ratio <= {HALF_DROP_RATIO} THEN 'half_of_equity'
       WHEN week_change_ratio <= {QUARTER_DROP_RATIO} THEN 'quarter_of_equity' END AS entry_band_code,
  CASE WHEN NOT is_setup_on THEN 'No action: the setup is off.'
       WHEN week_change_ratio <= {HALF_DROP_RATIO} THEN 'Entry: invest half of equity in the bear fund on Monday.'
       WHEN week_change_ratio <= {QUARTER_DROP_RATIO} THEN 'Entry: invest a quarter of equity in the bear fund on Monday.'
       WHEN week_change_ratio < 0 THEN 'No entry yet: the week fell less than 2.5%. On Monday to Wednesday a close 2.5% below this week close is an interim entry (a quarter of equity).'
       ELSE 'No entry: the S&P 500 did not fall this week.' END AS action_text
FROM bear
""")

dataset("ds_bear_checks", "Strategy 001 checks", f"""
WITH {STATES}, {BEAR},
vix AS (SELECT max_by(price_close, price_date) AS vix_close FROM {SILVER}.price_daily
        WHERE trading_symbol_code = '^VIX' AND price_date <= (SELECT week_end_date FROM bear)
          AND price_date > date_sub((SELECT week_end_date FROM bear), 7))
SELECT 1 AS step_number, 'Setup' AS step_group, 'A market climate light is red' AS check_name,
  CASE WHEN is_red THEN 'Yes' ELSE 'No' END AS answer_text, CAST(NULL AS STRING) AS value_text FROM bear
UNION ALL SELECT 2, 'Setup', 'The S&P 500 closed the week below its close {FIVE_WEEKS} weeks earlier',
  CASE WHEN week_close_amount < five_weeks_close_amount THEN 'Yes' ELSE 'No' END,
  concat(format_number(week_close_amount, 2), ' against ', format_number(five_weeks_close_amount, 2)) FROM bear
UNION ALL SELECT 3, 'Entry', 'The week fell 5% or more: invest half of equity',
  CASE WHEN week_change_ratio <= {HALF_DROP_RATIO} THEN 'Yes' ELSE 'No' END,
  concat(format_number(week_change_ratio * 100, 1), '% on the week') FROM bear
UNION ALL SELECT 4, 'Entry', 'The week fell 2.5% to 5%: invest a quarter of equity',
  CASE WHEN week_change_ratio <= {QUARTER_DROP_RATIO} AND week_change_ratio > {HALF_DROP_RATIO} THEN 'Yes' ELSE 'No' END,
  concat(format_number(week_change_ratio * 100, 1), '% on the week') FROM bear
UNION ALL SELECT 5, 'Entry', 'The week fell less than 2.5%: watch Monday to Wednesday for a 2.5% drop',
  CASE WHEN week_change_ratio < 0 AND week_change_ratio > {QUARTER_DROP_RATIO} THEN 'Yes' ELSE 'No' END,
  concat(format_number(week_change_ratio * 100, 1), '% on the week') FROM bear
UNION ALL SELECT 6, 'Exit', 'The week rose 3% or more: sell 10% of equity for every 3%',
  CASE WHEN week_change_ratio >= 0.03 THEN 'Yes' ELSE 'No' END,
  concat(format_number(week_change_ratio * 100, 1), '% on the week') FROM bear
UNION ALL SELECT 7, 'Exit', 'The week closed above its close {FIVE_WEEKS} weeks earlier: sell everything',
  CASE WHEN week_close_amount > five_weeks_close_amount THEN 'Yes' ELSE 'No' END,
  concat(format_number(week_close_amount, 2), ' against ', format_number(five_weeks_close_amount, 2)) FROM bear
UNION ALL SELECT 8, 'Exit', 'The VIX closed above 50: sell everything',
  CASE WHEN (SELECT vix_close FROM vix) > 50 THEN 'Yes' ELSE 'No' END,
  concat('VIX ', format_number((SELECT vix_close FROM vix), 1)) FROM bear
ORDER BY step_number
""")

dataset("ds_bear_funds", "Bear funds", f"""
WITH {FUND_ROWS},
prices AS (SELECT p.trading_symbol_code AS fund_code, p.price_date, p.price_close,
             row_number() OVER (PARTITION BY p.trading_symbol_code ORDER BY p.price_date DESC) AS recency
           FROM {SILVER}.price_daily p JOIN funds f ON f.fund_code = p.trading_symbol_code
           WHERE p.price_date <= {AS_OF_DATE})
SELECT f.fund_code, f.fund_name, f.fund_description, f.fund_order,
  max(CASE WHEN p.recency = 1 THEN p.price_date END) AS last_date,
  max(CASE WHEN p.recency = 1 THEN p.price_close END) AS last_close,
  max(CASE WHEN p.recency = 1 THEN p.price_close END) / max(CASE WHEN p.recency = 6 THEN p.price_close END) - 1 AS week_change_ratio
FROM funds f LEFT JOIN prices p ON p.fund_code = f.fund_code AND p.recency <= 6
GROUP BY f.fund_code, f.fund_name, f.fund_description, f.fund_order ORDER BY f.fund_order
""")

dataset("ds_fund_options", "Bear fund choices", f"""
WITH {FUND_ROWS} SELECT fund_code, fund_name, fund_description, fund_order FROM funds ORDER BY fund_order
""")

dataset("ds_bear_periods", "Past setup periods of strategy 001", f"""
WITH periods AS (
  SELECT setup_start_date, min(CASE WHEN event_code = 'setup_end' THEN event_date END) AS end_date,
         count_if(event_code = 'entry') AS entry_count
  FROM strategy_daily_event WHERE strategy_code = '{BEAR_FUND_CODE}' GROUP BY setup_start_date)
SELECT CAST(setup_start_date AS STRING) AS period_code,
  concat(CAST(setup_start_date AS STRING), ' to ', coalesce(CAST(end_date AS STRING), 'now'), ', ', entry_count,
         CASE WHEN entry_count = 1 THEN ' entry' ELSE ' entries' END) AS period_label, setup_start_date
FROM periods
UNION ALL SELECT 'all', 'All setup periods', DATE '1900-01-01'
ORDER BY setup_start_date DESC
""")

dataset("ds_bear_period_events", "Events of the chosen setup period", f"""
SELECT event_date, event_name, setup_start_date, entry_number, entry_band_code, week_close_amount, five_weeks_close_amount,
  week_change_ratio, reason_text
FROM strategy_daily_event
WHERE strategy_code = '{BEAR_FUND_CODE}' AND (:setup_period = 'all' OR CAST(setup_start_date AS STRING) = :setup_period)
ORDER BY event_date DESC
""")

dataset("ds_fund_chart", "Bear fund, S&P 500 and the setup periods", f"""
WITH fund AS (SELECT price_date, price_close FROM {SILVER}.price_daily
              WHERE trading_symbol_code = :fund_code AND price_date >= {HISTORY_START}),
sp500 AS (SELECT price_date, price_close AS sp500_close FROM {SILVER}.price_daily
          WHERE trading_symbol_code = '^GSPC' AND price_date >= {HISTORY_START}),
periods AS (SELECT setup_start_date AS start_date, min(CASE WHEN event_code = 'setup_end' THEN event_date END) AS end_date
            FROM strategy_daily_event WHERE strategy_code = '{BEAR_FUND_CODE}' GROUP BY setup_start_date),
entries AS (SELECT event_date, entry_band_code FROM strategy_daily_event
            WHERE strategy_code = '{BEAR_FUND_CODE}' AND event_code = 'entry')
SELECT f.price_date, f.price_close AS fund_close, s.sp500_close, p.start_date IS NOT NULL AS is_in_setup,
  e.entry_band_code, {HISTORY_DATES}
FROM fund f JOIN sp500 s ON s.price_date = f.price_date
LEFT JOIN periods p ON f.price_date >= p.start_date AND f.price_date < coalesce(p.end_date, DATE '9999-12-31')
LEFT JOIN entries e ON e.event_date = f.price_date
ORDER BY f.price_date
""")

dataset("ds_short_gate", "Market climate gate of strategy 002", f"""
WITH latest AS (SELECT max(signal_date) AS day FROM monitor_daily_signal
                WHERE monitor_code = 'market_climate' AND signal_code = 'climate' AND signal_date <= {AS_OF_DATE})
SELECT s.signal_date AS climate_date, max(CASE WHEN s.band_code = 'red' THEN 1 ELSE 0 END) = 1 AS is_red,
  concat_ws(', ', collect_list(concat(s.lens_name, ': ', s.band_code))) AS lights_text,
  CASE WHEN max(CASE WHEN s.band_code = 'red' THEN 1 ELSE 0 END) = 1 THEN 'Red light: the strategy can run'
       ELSE 'No red light: do not short' END AS gate_text,
  CASE WHEN max(CASE WHEN s.band_code = 'red' THEN 1 ELSE 0 END) = 1 THEN 'red' ELSE 'green' END AS gate_light
FROM monitor_daily_signal s JOIN latest l ON s.signal_date = l.day
WHERE s.monitor_code = 'market_climate' AND s.signal_code = 'climate' GROUP BY s.signal_date
""")

dataset("ds_short_candidates", "Short selling candidates of the week", f"""
WITH {STATES}, {SHORT_WEEK},
short AS (SELECT * FROM states WHERE strategy_code = '{SHORT_SELLING_CODE}' AND week_end_date = (SELECT day FROM short_week)),
starts AS (SELECT trading_symbol_code, max(setup_start_date) AS setup_start_date FROM strategy_daily_event
           WHERE strategy_code = '{SHORT_SELLING_CODE}' AND event_code = 'setup_start' AND event_date <= (SELECT day FROM short_week)
           GROUP BY trading_symbol_code),
entries AS (SELECT trading_symbol_code, setup_start_date, count(*) AS entry_count FROM strategy_daily_event
            WHERE strategy_code = '{SHORT_SELLING_CODE}' AND event_code = 'entry' AND event_date <= (SELECT day FROM short_week)
            GROUP BY trading_symbol_code, setup_start_date)
SELECT s.trading_symbol_code, c.company_name, st.setup_start_date, s.week_end_date, s.price_to_sales_ratio,
  s.down_week_count, s.week_change_ratio, 'green' AS setup_light,
  CASE WHEN coalesce(e.entry_count, 0) > 0 THEN 'green' ELSE 'grey' END AS entry_light
FROM short s
JOIN starts st ON st.trading_symbol_code = s.trading_symbol_code
LEFT JOIN entries e ON e.trading_symbol_code = s.trading_symbol_code AND e.setup_start_date = st.setup_start_date
LEFT JOIN {SILVER}.listing l ON l.listing_id = s.listing_id
LEFT JOIN {SILVER}.company c ON c.company_id = l.company_id
WHERE s.is_setup_on
ORDER BY s.down_week_count DESC, s.price_to_sales_ratio DESC
""")

dataset("ds_short_events", "Latest short selling events", f"""
SELECT e.event_date, e.trading_symbol_code, e.event_name, e.setup_start_date, e.entry_number, e.price_to_sales_ratio,
  e.down_week_count, e.reason_text
FROM strategy_daily_event e
WHERE e.strategy_code = '{SHORT_SELLING_CODE}' AND e.event_date <= {AS_OF_DATE}
ORDER BY e.event_date DESC, e.trading_symbol_code LIMIT 40
""")

dataset("ds_efficient_summary", "Strategy 004 efficient stocks screen of the day", f"""
WITH {EFFICIENT_DAY}, {EFFICIENT_SCREEN}
SELECT (SELECT day FROM screen_day) AS screen_date, count(*) AS screened_count,
  count_if(is_efficient AND is_liquid) AS passing_count,
  CASE WHEN count_if(is_efficient AND is_liquid) = 0 THEN 'No stock passes the screen'
       ELSE concat(count_if(is_efficient AND is_liquid), ' stock(s) pass the screen') END AS result_text,
  CASE WHEN count_if(is_efficient AND is_liquid) = 0 THEN 'grey' ELSE 'green' END AS result_light,
  max(efficiency_tr60_ratio) AS highest_tr60_ratio
FROM screen
""")

dataset("ds_efficient_closest", "Strategy 004 members closest to passing", f"""
WITH {EFFICIENT_DAY}, {EFFICIENT_SCREEN}
SELECT trading_symbol_code, company_name, efficiency_tr60_ratio, efficiency_r60_ratio, close_sixty_day_change_ratio,
  price_range_sixty_day_average_ratio, true_range_sixty_day_average_ratio, volume_sixty_day_average_count,
  CASE WHEN is_efficient THEN 'green' ELSE 'grey' END AS efficiency_light,
  CASE WHEN is_liquid THEN 'green' ELSE 'grey' END AS volume_light,
  CASE WHEN is_efficient AND is_liquid THEN 'green' ELSE 'grey' END AS pass_light
FROM screen ORDER BY efficiency_tr60_ratio DESC LIMIT 20
""")
