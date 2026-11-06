"""SQL of the market climate gold tables (openspec market-climate-gold, market-climate-dashboard).

Plain strings so a probe can run the exact query against dev before it goes into a pipeline. Table
names are two-part (`schema.table`), resolved in the pipeline's catalog.

`index_member_valuation_query()` is one row per member and day; `index_valuation_query()` sums its used
rows into one row per day.
"""

from common.market_climate import (
    INDEX_CODE,
    LISTING_VOLUME_WINDOW_ROWS,
    PRICE_MAX_AGE_DAYS,
)

DOMAIN = "silver_domain_investments"
US_CPI_RATE_CODE = "us_cpi_all_items_not_seasonally_adjusted"
FED_RATE_CODE = "us_federal_funds_target_upper"
CPI_LOOKBACK_DAYS = 120


def index_member_valuation_query() -> str:
    """One row per current member and day: its inputs, whether it is used and its effect on the index P/E."""
    return f"""
    WITH members AS (
      SELECT DISTINCT l.company_id, l.listing_id
      FROM {DOMAIN}.index_membership m
      JOIN {DOMAIN}.listing l ON l.listing_id = m.listing_id
      WHERE m.is_current AND l.company_id IS NOT NULL
    ), volume AS (
      SELECT listing_id, avg(price_volume_count) AS average_volume FROM (
        SELECT listing_id, price_volume_count,
               row_number() OVER (PARTITION BY listing_id ORDER BY price_date DESC) AS recency
        FROM {DOMAIN}.price_daily
      ) WHERE recency <= {LISTING_VOLUME_WINDOW_ROWS}
      GROUP BY listing_id
    ), main_listing AS (
      SELECT company_id, listing_id FROM (
        SELECT m.company_id, m.listing_id,
               row_number() OVER (
                 PARTITION BY m.company_id ORDER BY v.average_volume DESC NULLS LAST, m.listing_id
               ) AS pick
        FROM members m LEFT JOIN volume v ON v.listing_id = m.listing_id
      ) WHERE pick = 1
    ), days AS (
      SELECT p.price_date AS valuation_date
      FROM {DOMAIN}.price_daily p
      JOIN {DOMAIN}.listing l ON l.listing_id = p.listing_id
      WHERE l.trading_symbol_code = '^GSPC'
        AND p.price_date >= (
          SELECT min(q.price_date) FROM {DOMAIN}.price_daily q JOIN main_listing ml ON ml.listing_id = q.listing_id)
      GROUP BY p.price_date
    ), cpi_today AS (
      SELECT d.valuation_date, max_by(r.rate_value, r.observation_date) AS cpi_value
      FROM days d
      JOIN {DOMAIN}.market_rate_daily r
        ON r.rate_code = '{US_CPI_RATE_CODE}'
       AND r.observation_date <= d.valuation_date
       AND r.observation_date >= date_sub(d.valuation_date, {CPI_LOOKBACK_DAYS})
      GROUP BY d.valuation_date
    ), priced AS (
      SELECT valuation_date, company_id, listing_id, price_date, price_close, price_ingested_timestamp FROM (
        SELECT d.valuation_date, ml.company_id, ml.listing_id, p.price_date, p.price_close,
               p.ingested_timestamp AS price_ingested_timestamp,
               row_number() OVER (PARTITION BY d.valuation_date, ml.listing_id ORDER BY p.price_date DESC) AS pick
        FROM days d
        CROSS JOIN main_listing ml
        JOIN {DOMAIN}.price_daily p
          ON p.listing_id = ml.listing_id
         AND p.price_date <= d.valuation_date
         AND p.price_date >= date_sub(d.valuation_date, {PRICE_MAX_AGE_DAYS})
      ) WHERE pick = 1
    ), member_days AS (
      SELECT d.valuation_date, ml.company_id, ml.listing_id,
             p.price_date, p.price_close, p.price_ingested_timestamp,
             f.valid_from_date AS filing_valid_from_date,
             CASE WHEN f.shares_outstanding_count IS NOT NULL THEN 'cover_page'
                  WHEN f.weighted_average_shares_basic_count IS NOT NULL THEN 'weighted_average' END
               AS share_count_source_code,
             coalesce(f.shares_outstanding_count, f.weighted_average_shares_basic_count) AS share_count,
             f.net_income AS earnings_trailing_twelve_months_amount,
             f.revenue AS revenue_trailing_twelve_months_amount,
             f.earnings_ten_year_average_amount,
             f.earnings_ten_year_average_inflation_adjusted_amount AS adjusted_average_amount,
             f.earnings_year_count,
             f.consumer_price_index_value AS filing_consumer_price_index_value,
             c.cpi_value AS consumer_price_index_value,
             f.ingested_timestamp AS fundamentals_ingested_timestamp
      FROM days d
      JOIN cpi_today c ON c.valuation_date = d.valuation_date
      CROSS JOIN main_listing ml
      LEFT JOIN priced p ON p.valuation_date = d.valuation_date AND p.company_id = ml.company_id
      LEFT JOIN {DOMAIN}.company_fundamentals f
        ON f.company_id = ml.company_id AND d.valuation_date BETWEEN f.valid_from_date AND f.valid_to_date
    ), reasoned AS (
      SELECT m.*,
             CASE WHEN m.price_close IS NULL THEN 'no_recent_price'
                  WHEN m.filing_valid_from_date IS NULL THEN 'no_filing'
                  WHEN m.share_count IS NULL THEN 'no_share_count'
                  WHEN m.earnings_trailing_twelve_months_amount IS NULL THEN 'no_net_income'
                  WHEN m.earnings_ten_year_average_amount IS NULL
                    OR m.adjusted_average_amount IS NULL THEN 'no_ten_year_average'
                  WHEN m.filing_consumer_price_index_value IS NULL THEN 'no_consumer_price_index'
             END AS exclusion_reason_code
      FROM member_days m
    ), valued AS (
      SELECT r.*,
             r.exclusion_reason_code IS NULL AS is_used,
             r.price_close * r.share_count AS market_value_amount,
             r.adjusted_average_amount
               * CAST(r.consumer_price_index_value / r.filing_consumer_price_index_value AS DECIMAL(18, 10))
               AS earnings_ten_year_average_inflation_adjusted_amount
      FROM reasoned r
    ), totals AS (
      SELECT v.*,
             sum(CASE WHEN is_used THEN market_value_amount END) OVER (PARTITION BY valuation_date)
               AS index_market_value_amount,
             sum(CASE WHEN is_used THEN earnings_ten_year_average_inflation_adjusted_amount END)
               OVER (PARTITION BY valuation_date) AS index_earnings_amount
      FROM valued v
    ), positioned AS (
      SELECT t.*,
             CASE WHEN index_earnings_amount > 0
                  THEN CAST(index_market_value_amount / index_earnings_amount AS DECIMAL(18, 4)) END AS index_ratio,
             CASE WHEN is_used AND earnings_ten_year_average_inflation_adjusted_amount > 0
                  THEN CAST(market_value_amount / earnings_ten_year_average_inflation_adjusted_amount
                            AS DECIMAL(18, 4)) END AS own_ratio,
             CASE WHEN is_used AND index_earnings_amount - earnings_ten_year_average_inflation_adjusted_amount > 0
                  THEN CAST((index_market_value_amount - market_value_amount)
                            / (index_earnings_amount - earnings_ten_year_average_inflation_adjusted_amount)
                            AS DECIMAL(18, 4)) END AS without_ratio
      FROM totals t
    )
    SELECT '{INDEX_CODE}' AS index_code,
           valuation_date,
           company_id,
           listing_id,
           price_date,
           filing_valid_from_date,
           price_close,
           share_count,
           share_count_source_code,
           earnings_trailing_twelve_months_amount,
           revenue_trailing_twelve_months_amount,
           earnings_ten_year_average_amount,
           earnings_year_count,
           filing_consumer_price_index_value,
           consumer_price_index_value,
           earnings_ten_year_average_inflation_adjusted_amount,
           market_value_amount,
           is_used,
           exclusion_reason_code,
           CASE WHEN is_used AND index_market_value_amount > 0
                THEN CAST(market_value_amount / index_market_value_amount AS DECIMAL(18, 10)) END
             AS market_value_share_ratio,
           own_ratio AS price_earnings_ten_year_average_inflation_adjusted_ratio,
           without_ratio AS price_earnings_without_member_ratio,
           CASE WHEN is_used AND index_ratio IS NOT NULL AND without_ratio IS NOT NULL
                THEN index_ratio - without_ratio END AS price_earnings_effect_ratio,
           CASE WHEN market_value_amount IS NOT NULL AND revenue_trailing_twelve_months_amount > 0
                THEN CAST(market_value_amount / revenue_trailing_twelve_months_amount AS DECIMAL(18, 4)) END
             AS price_to_sales_ratio,
           'USD' AS currency_code,
           CASE WHEN price_ingested_timestamp IS NULL THEN fundamentals_ingested_timestamp
                WHEN fundamentals_ingested_timestamp IS NULL THEN price_ingested_timestamp
                ELSE least(price_ingested_timestamp, fundamentals_ingested_timestamp) END AS ingested_timestamp
    FROM positioned
    """


def index_valuation_query(member_source: str = "valuation_daily_index_member") -> str:
    """One row per day: the S&P 500's market value, earnings totals, P/E ratios and coverage counts.

    `member_source` is the member valuation per day: a table or a parenthesised query.
    """
    return f"""
    WITH totals AS (
      SELECT valuation_date,
             max(consumer_price_index_value) AS consumer_price_index_value,
             count(*) AS member_count,
             count_if(is_used) AS members_used_count,
             count_if(price_close IS NOT NULL AND share_count IS NULL) AS members_without_shares_count,
             count_if(is_used AND earnings_year_count < 10) AS members_under_ten_years_count,
             CAST(sum(CASE WHEN is_used THEN market_value_amount END) AS DECIMAL(34, 2)) AS market_value_amount,
             CAST(sum(CASE WHEN is_used THEN earnings_trailing_twelve_months_amount END) AS DECIMAL(34, 2))
               AS earnings_trailing_twelve_months_amount,
             CAST(sum(CASE WHEN is_used THEN earnings_ten_year_average_amount END) AS DECIMAL(34, 2))
               AS earnings_ten_year_average_amount,
             CAST(sum(CASE WHEN is_used THEN earnings_ten_year_average_inflation_adjusted_amount END)
                  AS DECIMAL(34, 2)) AS earnings_ten_year_average_inflation_adjusted_amount,
             min(CASE WHEN is_used THEN ingested_timestamp END) AS ingested_timestamp
      FROM {member_source}
      GROUP BY valuation_date
    )
    SELECT '{INDEX_CODE}' AS index_code,
           valuation_date,
           market_value_amount,
           earnings_trailing_twelve_months_amount,
           earnings_ten_year_average_amount,
           earnings_ten_year_average_inflation_adjusted_amount,
           CASE WHEN earnings_trailing_twelve_months_amount > 0
                THEN CAST(market_value_amount / earnings_trailing_twelve_months_amount AS DECIMAL(18, 4))
           END AS price_earnings_trailing_twelve_months_ratio,
           CASE WHEN earnings_ten_year_average_amount > 0
                THEN CAST(market_value_amount / earnings_ten_year_average_amount AS DECIMAL(18, 4))
           END AS price_earnings_ten_year_average_ratio,
           CASE WHEN earnings_ten_year_average_inflation_adjusted_amount > 0
                THEN CAST(market_value_amount / earnings_ten_year_average_inflation_adjusted_amount AS DECIMAL(18, 4))
           END AS price_earnings_ten_year_average_inflation_adjusted_ratio,
           consumer_price_index_value,
           member_count,
           members_used_count,
           members_without_shares_count,
           members_under_ten_years_count,
           'USD' AS currency_code,
           ingested_timestamp
    FROM totals
    WHERE members_used_count > 0
    """
