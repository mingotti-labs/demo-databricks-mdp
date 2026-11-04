"""SQL of the market climate gold tables (openspec market-climate-gold).

Plain strings so a probe can run the exact query against dev before it goes into a pipeline. Table
names are two-part (`schema.table`), resolved in the pipeline's catalog.
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


def index_valuation_query() -> str:
    """One row per day: the S&P 500's market value, earnings totals, P/E ratios and coverage counts."""
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
    ), cpi_today AS (
      SELECT d.valuation_date, max_by(r.rate_value, r.observation_date) AS cpi_value
      FROM days d
      JOIN {DOMAIN}.market_rate_daily r
        ON r.rate_code = '{US_CPI_RATE_CODE}'
       AND r.observation_date <= d.valuation_date
       AND r.observation_date >= date_sub(d.valuation_date, {CPI_LOOKBACK_DAYS})
      GROUP BY d.valuation_date
    ), priced AS (
      SELECT valuation_date, company_id, price_close, price_ingested_timestamp FROM (
        SELECT d.valuation_date, ml.company_id, p.price_close, p.ingested_timestamp AS price_ingested_timestamp,
               row_number() OVER (PARTITION BY d.valuation_date, ml.listing_id ORDER BY p.price_date DESC) AS pick
        FROM days d
        CROSS JOIN main_listing ml
        JOIN {DOMAIN}.price_daily p
          ON p.listing_id = ml.listing_id
         AND p.price_date <= d.valuation_date
         AND p.price_date >= date_sub(d.valuation_date, {PRICE_MAX_AGE_DAYS})
      ) WHERE pick = 1
    ), member_days AS (
      SELECT d.valuation_date, ml.company_id,
             p.price_close, p.price_ingested_timestamp,
             coalesce(f.shares_outstanding_count, f.weighted_average_shares_basic_count) AS share_count,
             f.net_income,
             f.earnings_ten_year_average_amount,
             f.earnings_ten_year_average_inflation_adjusted_amount,
             f.consumer_price_index_value AS row_cpi,
             f.earnings_year_count,
             f.ingested_timestamp AS fundamentals_ingested_timestamp
      FROM days d
      CROSS JOIN main_listing ml
      LEFT JOIN priced p ON p.valuation_date = d.valuation_date AND p.company_id = ml.company_id
      LEFT JOIN {DOMAIN}.company_fundamentals f
        ON f.company_id = ml.company_id AND d.valuation_date BETWEEN f.valid_from_date AND f.valid_to_date
    ), valued AS (
      SELECT m.*,
             c.cpi_value AS cpi_today_value,
             m.price_close IS NOT NULL AND m.share_count IS NOT NULL AND m.net_income IS NOT NULL
               AND m.earnings_ten_year_average_amount IS NOT NULL
               AND m.earnings_ten_year_average_inflation_adjusted_amount IS NOT NULL
               AND m.row_cpi IS NOT NULL AND c.cpi_value IS NOT NULL AS is_used
      FROM member_days m
      JOIN cpi_today c ON c.valuation_date = m.valuation_date
    ), totals AS (
      SELECT valuation_date,
             max(cpi_today_value) AS consumer_price_index_value,
             count(*) AS member_count,
             count_if(is_used) AS members_used_count,
             count_if(price_close IS NOT NULL AND share_count IS NULL) AS members_without_shares_count,
             count_if(is_used AND earnings_year_count < 10) AS members_under_ten_years_count,
             CAST(sum(CASE WHEN is_used THEN price_close * share_count END) AS DECIMAL(34, 2)) AS market_value_amount,
             CAST(sum(CASE WHEN is_used THEN net_income END) AS DECIMAL(34, 2))
               AS earnings_trailing_twelve_months_amount,
             CAST(sum(CASE WHEN is_used THEN earnings_ten_year_average_amount END) AS DECIMAL(34, 2))
               AS earnings_ten_year_average_amount,
             CAST(sum(CASE WHEN is_used THEN
                   earnings_ten_year_average_inflation_adjusted_amount
                   * CAST(cpi_today_value / row_cpi AS DECIMAL(18, 10)) END) AS DECIMAL(34, 2))
               AS earnings_ten_year_average_inflation_adjusted_amount,
             least(min(CASE WHEN is_used THEN price_ingested_timestamp END),
                   min(CASE WHEN is_used THEN fundamentals_ingested_timestamp END)) AS ingested_timestamp
      FROM valued
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
