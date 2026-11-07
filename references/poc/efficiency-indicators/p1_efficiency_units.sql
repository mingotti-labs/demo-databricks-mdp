-- P1: efficiency ratio of the S&P 500 members on the latest price date, with the 60-day range average in dollars and in percent of the close.
WITH p AS (
  SELECT listing_id, trading_symbol_code, price_date, price_close, price_high, price_low, price_close_adjusted, price_volume_count,
         lag(price_close) OVER (PARTITION BY listing_id ORDER BY price_date) AS previous_close
  FROM mdp_prd.silver_domain_investments.price_daily
), r AS (
  SELECT *,
         price_high - price_low AS day_range,
         greatest(price_high, previous_close) - least(price_low, previous_close) AS true_range
  FROM p
), w AS (
  SELECT *,
         (price_close_adjusted / lag(price_close_adjusted, 60) OVER o - 1) * 100 AS roc_60_percent,
         avg(day_range) OVER w60 AS range_sma_60,
         avg(true_range) OVER w60 AS true_range_sma_60,
         avg(day_range / price_close * 100) OVER w60 AS range_percent_sma_60,
         avg(true_range / price_close * 100) OVER w60 AS true_range_percent_sma_60,
         avg(price_volume_count) OVER w60 AS volume_sma_60
  FROM r
  WINDOW o AS (PARTITION BY listing_id ORDER BY price_date),
         w60 AS (PARTITION BY listing_id ORDER BY price_date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW)
), latest AS (
  SELECT w.* FROM w
  JOIN mdp_prd.silver_domain_investments.index_membership m USING (listing_id)
  WHERE w.price_date = (SELECT max(price_date) FROM mdp_prd.silver_domain_investments.price_daily WHERE trading_symbol_code = '^GSPC')
)
SELECT count(*) AS members,
       count_if(roc_60_percent / range_sma_60 >= 15) AS er_dollars_15,
       count_if(roc_60_percent / range_percent_sma_60 >= 15) AS er_percent_15,
       count_if(roc_60_percent / true_range_percent_sma_60 >= 15) AS ert_percent_15,
       percentile(roc_60_percent / range_sma_60, 0.9) AS er_dollars_p90,
       percentile(roc_60_percent / range_percent_sma_60, 0.9) AS er_percent_p90,
       max(roc_60_percent / range_percent_sma_60) AS er_percent_max,
       count_if(volume_sma_60 > 200000) AS volume_ok
FROM latest
