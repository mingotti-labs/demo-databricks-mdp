"""Dataset queries of the Market climate dashboard (openspec market-climate-dashboard).

Bare table names: the dashboard's dataset catalog and schema (`gold_analytics_gateway` of the target's
catalog) fill them in; silver tables carry their schema name. `:as_of_date` is a dashboard date parameter
(default today); the day shown is the latest day with a climate row on or before it.
"""

AS_OF = (
    "asof AS (SELECT max(signal_date) AS day FROM monitor_daily_signal "
    "WHERE signal_code = 'climate' AND signal_date <= coalesce(:as_of_date, DATE '9999-12-31'))"
)
VALUATION_AS_OF = (
    "asof AS (SELECT max(valuation_date) AS day FROM valuation_daily_index "
    "WHERE valuation_date <= coalesce(:as_of_date, DATE '9999-12-31'))"
)

DATASETS: dict[str, tuple[str, str]] = {}


def dataset(name: str, title: str, query: str) -> None:
    DATASETS[name] = (title, " ".join(query.split()) + " ")


dataset("ds_freshness", "Data dates", f"""
WITH {AS_OF}
SELECT (SELECT day FROM asof) AS climate_date,
  (SELECT max(price_date) FROM silver_domain_investments.price_indicator_daily WHERE trading_symbol_code = '^GSPC') AS sp500_price_date,
  (SELECT max(observation_date) FROM silver_domain_investments.market_rate_daily WHERE rate_code = 'us_federal_funds_target_upper') AS fed_rate_date,
  (SELECT max(observation_date) FROM silver_domain_investments.market_rate_daily WHERE rate_code = 'us_cpi_all_items_not_seasonally_adjusted') AS cpi_date
""")

dataset("ds_lights", "Lights of the day", f"""
WITH {AS_OF}
SELECT s.lens_name, s.lens_code, s.yes_count, s.band_code AS light_code, s.action_name, s.reason_text, s.signal_date AS climate_date
FROM monitor_daily_signal s JOIN asof a ON s.signal_date = a.day
WHERE s.signal_code = 'climate' ORDER BY s.lens_code
""")

dataset("ds_answers", "Answers of the day", f"""
WITH {AS_OF}
SELECT s.lens_name, s.lens_code, s.signal_name, s.signal_code,
  CASE WHEN s.is_yes THEN 'Yes' ELSE 'No' END AS answer_text,
  s.band_code, s.measured_value, s.threshold_value, s.reason_text
FROM monitor_daily_signal s JOIN asof a ON s.signal_date = a.day
WHERE s.signal_code <> 'climate' ORDER BY s.lens_code, s.signal_code
""")

dataset("ds_light_history", "Light history", """
SELECT signal_date, lens_name, lens_code, yes_count, band_code AS light_code
FROM monitor_daily_signal WHERE signal_code = 'climate' ORDER BY signal_date, lens_name
""")

dataset("ds_pe_history", "Price/earnings history", """
SELECT i.valuation_date,
  i.price_earnings_ten_year_average_inflation_adjusted_ratio AS pe_ten_year_adjusted,
  i.price_earnings_trailing_twelve_months_ratio AS pe_trailing
FROM valuation_daily_index i ORDER BY i.valuation_date
""")

dataset("ds_fed_history", "Fed target rate", """
SELECT signal_date, measured_value AS fed_target_rate, band_code AS fed_band_code
FROM monitor_daily_signal WHERE signal_code = 'fed_in_the_way' AND lens_code = 'long_run' AND signal_date >= DATE '2022-01-01'
ORDER BY signal_date
""")

dataset("ds_trend_history", "S&P 500 and its 200-day average", """
SELECT signal_date, measured_value AS sp500_close, threshold_value AS sp500_average_200
FROM monitor_daily_signal WHERE signal_code = 'market_going_up' AND lens_code = 'long_run' AND signal_date >= DATE '2022-01-01'
ORDER BY signal_date
""")

MEMBER_COLUMNS = (
    "c.company_name, c.gics_sector_name AS sector_name, m.market_value_share_ratio, "
    "m.price_earnings_ten_year_average_inflation_adjusted_ratio AS member_pe, "
    "CASE WHEN m.earnings_trailing_twelve_months_amount > 0 THEN m.market_value_amount / m.earnings_trailing_twelve_months_amount END AS member_pe_trailing, "
    "m.price_earnings_without_member_ratio AS pe_without_member, m.price_earnings_effect_ratio AS pe_effect"
)
MEMBER_JOIN = (
    "FROM valuation_daily_index_member m JOIN asof a ON m.valuation_date = a.day "
    "JOIN silver_domain_investments.company c ON c.company_id = m.company_id"
)

dataset("ds_index_day", "Index of the day", f"""
WITH {VALUATION_AS_OF}
SELECT i.valuation_date, i.market_value_amount / 1e12 AS market_value_trillion,
  i.earnings_ten_year_average_inflation_adjusted_amount / 1e9 AS earnings_adjusted_billion,
  i.price_earnings_ten_year_average_inflation_adjusted_ratio AS pe_ten_year_adjusted,
  i.price_earnings_trailing_twelve_months_ratio AS pe_trailing,
  i.members_used_count, i.member_count, i.members_without_shares_count, i.members_under_ten_years_count
FROM valuation_daily_index i JOIN asof a ON i.valuation_date = a.day
""")

dataset("ds_top_up", "Members pushing the P/E up", f"""
WITH {VALUATION_AS_OF}
SELECT {MEMBER_COLUMNS} {MEMBER_JOIN} WHERE m.is_used AND m.price_earnings_effect_ratio IS NOT NULL
ORDER BY m.price_earnings_effect_ratio DESC LIMIT 10
""")

dataset("ds_top_down", "Members pushing the P/E down", f"""
WITH {VALUATION_AS_OF}
SELECT {MEMBER_COLUMNS} {MEMBER_JOIN} WHERE m.is_used AND m.price_earnings_effect_ratio IS NOT NULL
ORDER BY m.price_earnings_effect_ratio ASC LIMIT 10
""")

dataset("ds_excluded", "Members left out", f"""
WITH {VALUATION_AS_OF}
SELECT c.company_name, c.gics_sector_name AS sector_name, m.exclusion_reason_code, m.price_date
{MEMBER_JOIN} WHERE NOT m.is_used ORDER BY m.exclusion_reason_code, c.company_name
""")

dataset("ds_members", "All members", f"""
WITH {VALUATION_AS_OF}
SELECT {MEMBER_COLUMNS}, m.is_used, m.exclusion_reason_code, m.price_close, m.share_count,
  m.market_value_amount / 1e9 AS market_value_billion
{MEMBER_JOIN} ORDER BY m.market_value_amount DESC NULLS LAST
""")

dataset("ds_checks", "Checks of the day", f"""
WITH {VALUATION_AS_OF},
sums AS (SELECT count_if(m.is_used) AS used_count, sum(CASE WHEN m.is_used THEN m.market_value_amount END) AS value,
  sum(CASE WHEN m.is_used THEN m.earnings_ten_year_average_inflation_adjusted_amount END) AS earnings
  FROM valuation_daily_index_member m JOIN asof a ON m.valuation_date = a.day)
SELECT i.members_used_count AS index_used_count, s.used_count AS member_used_count,
  round(i.market_value_amount - s.value, 2) AS market_value_difference_amount,
  round(i.earnings_ten_year_average_inflation_adjusted_amount - s.earnings, 2) AS earnings_difference_amount,
  i.price_earnings_ten_year_average_inflation_adjusted_ratio AS pe_index,
  round(s.value / s.earnings, 4) AS pe_from_members
FROM valuation_daily_index i JOIN asof a ON i.valuation_date = a.day CROSS JOIN sums s
""")

dataset("ds_sectors", "Sectors of the day", f"""
WITH {VALUATION_AS_OF},
used AS (SELECT c.gics_sector_name AS sector_name, m.market_value_amount AS value,
  m.earnings_ten_year_average_inflation_adjusted_amount AS earnings, m.price_earnings_effect_ratio AS effect
  FROM valuation_daily_index_member m JOIN asof a ON m.valuation_date = a.day
  JOIN silver_domain_investments.company c ON c.company_id = m.company_id WHERE m.is_used),
total AS (SELECT sum(value) AS value, sum(earnings) AS earnings FROM used)
SELECT u.sector_name, count(*) AS member_count, sum(u.value) / 1e12 AS market_value_trillion,
  sum(u.value) / total.value AS market_value_share_ratio,
  CASE WHEN sum(u.earnings) > 0 THEN sum(u.value) / sum(u.earnings) END AS sector_pe,
  CASE WHEN total.earnings - sum(u.earnings) > 0
       THEN (total.value - sum(u.value)) / (total.earnings - sum(u.earnings)) END AS pe_without_sector,
  total.value / total.earnings AS pe_index
FROM used u CROSS JOIN total GROUP BY u.sector_name, total.value, total.earnings ORDER BY sum(u.value) DESC
""")

SECTOR_MEMBERS = f"""
WITH {VALUATION_AS_OF}
SELECT {MEMBER_COLUMNS}, m.price_earnings_effect_ratio AS pe_effect_sort
{MEMBER_JOIN} WHERE m.is_used AND c.gics_sector_name = :sector_name
"""
dataset("ds_sector_up", "Sector members pushing the P/E up", SECTOR_MEMBERS + " ORDER BY m.price_earnings_effect_ratio DESC LIMIT 10")
dataset("ds_sector_down", "Sector members pushing the P/E down", SECTOR_MEMBERS + " AND m.price_earnings_effect_ratio IS NOT NULL ORDER BY m.price_earnings_effect_ratio ASC LIMIT 10")
dataset("ds_sector_names", "Sector names", "SELECT DISTINCT gics_sector_name AS sector_name FROM silver_domain_investments.company WHERE gics_sector_name IS NOT NULL ORDER BY 1")

COMPANY_NAMES = (
    "SELECT DISTINCT c.company_name FROM valuation_daily_index_member m "
    "JOIN silver_domain_investments.company c ON c.company_id = m.company_id ORDER BY 1"
)
dataset("ds_company_names", "Company names", COMPANY_NAMES)

dataset("ds_company_check", "Company check, step by step", f"""
WITH {VALUATION_AS_OF},
m AS (SELECT m.*, c.company_name FROM valuation_daily_index_member m JOIN asof a ON m.valuation_date = a.day
  JOIN silver_domain_investments.company c ON c.company_id = m.company_id WHERE c.company_name = :company_name),
steps AS (
  SELECT 1 AS step_number, 'Closing price' AS step_name, format_number(price_close, 2) || ' US$ on ' || CAST(price_date AS STRING) AS value_text, 'Latest close on or before the day' AS how_text FROM m
  UNION ALL SELECT 2, 'Shares outstanding', format_number(share_count, 0) || ' (' || coalesce(share_count_source_code, 'none') || ')', 'From the latest filing' FROM m
  UNION ALL SELECT 3, 'Market value', format_number(market_value_amount / 1e9, 2) || ' US$ billion', 'Step 1 x step 2' FROM m
  UNION ALL SELECT 4, 'Earnings, trailing 12 months', format_number(earnings_trailing_twelve_months_amount / 1e6, 1) || ' US$ million', 'Net income of the latest 12 months' FROM m
  UNION ALL SELECT 5, 'P/E on trailing earnings (what finance sites show)', format_number(market_value_amount / nullif(earnings_trailing_twelve_months_amount, 0), 2), 'Step 3 / step 4' FROM m
  UNION ALL SELECT 6, 'Earnings, average of the last ' || coalesce(CAST(earnings_year_count AS STRING), '0') || ' years', format_number(earnings_ten_year_average_amount / 1e6, 1) || ' US$ million', 'Average yearly net income, up to 10 years' FROM m
  UNION ALL SELECT 7, 'Inflation factor', format_number(consumer_price_index_value / nullif(filing_consumer_price_index_value, 0), 4), 'Price index today / price index at the filing' FROM m
  UNION ALL SELECT 8, 'Average earnings in today''s money', format_number(earnings_ten_year_average_inflation_adjusted_amount / 1e6, 1) || ' US$ million', 'Step 6 x step 7' FROM m
  UNION ALL SELECT 9, 'P/E on 10-year inflation-adjusted earnings (the climate uses this)', format_number(price_earnings_ten_year_average_inflation_adjusted_ratio, 2), 'Step 3 / step 8' FROM m
  UNION ALL SELECT 10, 'Index P/E without this member', format_number(price_earnings_without_member_ratio, 2), 'Same calculation over the other members' FROM m
  UNION ALL SELECT 11, 'Effect on the index P/E', format_number(price_earnings_effect_ratio, 4), 'Index P/E minus step 10' FROM m
  UNION ALL SELECT 12, 'Used in the index', CASE WHEN is_used THEN 'Yes' ELSE 'No: ' || exclusion_reason_code END, 'A member is left out when an input is missing' FROM m)
SELECT step_number, step_name, value_text, how_text FROM steps ORDER BY step_number
""")

RANGE_START = """CASE :range_code
  WHEN '5D' THEN date_sub(last_date, 7) WHEN '1M' THEN add_months(last_date, -1) WHEN '6M' THEN add_months(last_date, -6)
  WHEN 'YTD' THEN trunc(last_date, 'YEAR') ELSE add_months(last_date, -12) END"""
COMPANY_PRICES = f"""
WITH {VALUATION_AS_OF},
listing AS (SELECT m.listing_id FROM valuation_daily_index_member m JOIN asof a ON m.valuation_date = a.day
  JOIN silver_domain_investments.company c ON c.company_id = m.company_id WHERE c.company_name = :company_name),
prices AS (SELECT p.price_date, p.price_close, p.price_high, p.price_low,
  avg(p.price_close) OVER w AS band_middle, stddev_pop(p.price_close) OVER w AS band_deviation, count(*) OVER w AS window_count,
  max(p.price_date) OVER () AS last_date
  FROM silver_domain_investments.price_daily p JOIN listing l ON l.listing_id = p.listing_id
  WHERE p.price_date <= (SELECT day FROM asof)
  WINDOW w AS (ORDER BY p.price_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW))
"""
dataset("ds_range_options", "Price ranges", "SELECT * FROM VALUES ('5D', 1), ('1M', 2), ('6M', 3), ('YTD', 4), ('1Y', 5) AS t(range_code, range_order) ORDER BY range_order")

dataset("ds_company_price", "Company price with Bollinger bands", COMPANY_PRICES + f"""
SELECT price_date, price_close, band_middle, band_middle + 2 * band_deviation AS band_upper, band_middle - 2 * band_deviation AS band_lower
FROM prices WHERE window_count = 20 AND price_date >= {RANGE_START} ORDER BY price_date
""")

dataset("ds_company_figures", "Company price figures", COMPANY_PRICES + """
, ranked AS (SELECT *, row_number() OVER (ORDER BY price_date DESC) AS recency FROM prices)
SELECT max(CASE WHEN recency = 1 THEN price_close END) AS last_close,
  max(CASE WHEN recency = 1 THEN price_close END) / max(CASE WHEN recency = 2 THEN price_close END) - 1 AS day_change_ratio,
  max(CASE WHEN price_date > add_months(last_date, -12) THEN price_high END) AS high_52_weeks,
  min(CASE WHEN price_date > add_months(last_date, -12) THEN price_low END) AS low_52_weeks,
  max(last_date) AS price_date
FROM ranked
""")
