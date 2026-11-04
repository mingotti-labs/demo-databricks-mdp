# Databricks notebook source
# MAGIC %md
# MAGIC # Probe P1: 10-year inflation-adjusted P/E with real data (market climate story)
# MAGIC Read only, no tables written. Reads `silver_domain_investments` in the given catalog.
# MAGIC 1. One company end to end (Apple): its last 10 10-Ks, CPI, factor, adjusted earnings, P/E.
# MAGIC 2. The index today: totals, both P/Es, members with fewer than 10 years, top contributors.
# MAGIC 3. Share-class check: what SEC reports as shares for companies with several listings.
# MAGIC 4. A small history of the index P/E at a few dates (today's members, point in time filings).

# COMMAND ----------

dbutils.widgets.text("catalog", "mdp_dev")
catalog = dbutils.widgets.get("catalog")
spark.sql(f"USE {catalog}.silver_domain_investments")
summary = []


def num(value, spec=",.0f"):
    """Format a number, or show "none" when the value is missing."""
    return "none" if value is None else format(value, spec)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Shared views
# MAGIC - `cpi`: US CPI all items, not seasonally adjusted, one value per month (the month's first business day).
# MAGIC - `annual`: one row per company and fiscal year end: the latest 10-K or 10-K/A for that year end,
# MAGIC   with the date it was filed (the date it became known).
# MAGIC - `price_last`: each listing's close on a date (the last trading day on or before it).

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TEMP VIEW cpi AS
SELECT date_trunc('MONTH', observation_date) AS month_date, first(rate_value) AS cpi_value
FROM market_rate_daily
WHERE rate_code = 'us_cpi_all_items_not_seasonally_adjusted'
GROUP BY 1
""")

spark.sql("""
CREATE OR REPLACE TEMP VIEW annual AS
SELECT company_id, central_index_key, period_end_date, valid_from_date AS filed_date, form_code,
       net_income, shares_outstanding_count
FROM (
  SELECT *, row_number() OVER (PARTITION BY company_id, period_end_date ORDER BY valid_from_date DESC) AS pick
  FROM company_fundamentals
  WHERE form_code LIKE '10-K%' AND net_income IS NOT NULL
) WHERE pick = 1
""")

latest_cpi = spark.sql("SELECT month_date, cpi_value FROM cpi ORDER BY month_date DESC LIMIT 1").first()
summary.append(f"CPI today: {latest_cpi.cpi_value} ({latest_cpi.month_date:%Y-%m})")
print(summary[-1])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Apple end to end

# COMMAND ----------

apple = spark.sql(f"""
WITH a AS (
  SELECT a.period_end_date, a.filed_date, a.form_code, a.net_income, c.cpi_value
  FROM annual a
  JOIN company co ON co.company_id = a.company_id
  JOIN cpi c ON c.month_date = date_trunc('MONTH', a.period_end_date)
  WHERE co.company_name = 'Apple Inc.'
  ORDER BY a.period_end_date DESC LIMIT 10
)
SELECT year(period_end_date) AS fiscal_year, period_end_date, filed_date, form_code,
       round(net_income / 1e9, 2) AS earnings_billion,
       cpi_value,
       round({latest_cpi.cpi_value} / cpi_value, 3) AS factor,
       round(net_income * {latest_cpi.cpi_value} / cpi_value / 1e9, 2) AS earnings_today_money_billion
FROM a ORDER BY period_end_date
""")
display(apple)
rows = apple.collect()
summary.append("Apple: year | earnings bn | CPI | factor | today's money bn")
summary += [f"  {r.fiscal_year} | {r.earnings_billion} | {r.cpi_value} | {r.factor} | {r.earnings_today_money_billion}" for r in rows]

apple_mv = spark.sql("""
WITH shares AS (
  SELECT f.company_id, f.shares_outstanding_count, f.net_income AS trailing_net_income
  FROM company_fundamentals f JOIN company co ON co.company_id = f.company_id
  WHERE co.company_name = 'Apple Inc.' AND f.valid_to_date = DATE '9999-12-31'
), px AS (
  SELECT p.price_close, p.price_date FROM price_daily p JOIN listing l ON l.listing_id = p.listing_id
  WHERE l.trading_symbol_code = 'AAPL' ORDER BY p.price_date DESC LIMIT 1
)
SELECT px.price_date, px.price_close, s.shares_outstanding_count,
       px.price_close * s.shares_outstanding_count AS market_value, s.trailing_net_income
FROM shares s CROSS JOIN px
""").first()
avg_real = sum(r.earnings_today_money_billion for r in rows) / len(rows)
mv_bn = float(apple_mv.market_value) / 1e9
summary.append(
    f"Apple on {apple_mv.price_date}: close {apple_mv.price_close}, shares {apple_mv.shares_outstanding_count:,}, "
    f"market value {mv_bn:,.1f} bn; 10-year average in today's money {avg_real:.2f} bn; "
    f"P/E (10-year) {mv_bn / avg_real:.1f}; trailing P/E {mv_bn / (float(apple_mv.trailing_net_income) / 1e9):.1f}"
)
print("\n".join(summary))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. The index today
# MAGIC Current members; one listing per company (the most traded one) for the price; shares and
# MAGIC trailing earnings from the latest filing; the 10-year average from the last 10 10-Ks.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TEMP VIEW company_today AS
WITH members AS (
  SELECT DISTINCT l.company_id FROM index_membership m JOIN listing l ON l.listing_id = m.listing_id
  WHERE m.is_current AND l.company_id IS NOT NULL
), main_listing AS (
  SELECT company_id, listing_id, trading_symbol_code FROM (
    SELECT l.company_id, l.listing_id, l.trading_symbol_code,
           row_number() OVER (PARTITION BY l.company_id ORDER BY avg(p.price_volume_count) DESC) AS pick
    FROM listing l JOIN members m ON m.company_id = l.company_id
    JOIN price_daily p ON p.listing_id = l.listing_id AND p.price_date >= date_sub(current_date(), 60)
    GROUP BY l.company_id, l.listing_id, l.trading_symbol_code
  ) WHERE pick = 1
), px AS (
  SELECT listing_id, max_by(price_close, price_date) AS price_close, max(price_date) AS price_date
  FROM price_daily GROUP BY listing_id
), latest AS (
  SELECT company_id, shares_outstanding_count, net_income AS trailing_net_income
  FROM company_fundamentals WHERE valid_to_date = DATE '9999-12-31'
), ten AS (
  SELECT company_id, count(*) AS year_count,
         avg(net_income * {latest_cpi.cpi_value} / c.cpi_value) AS average_real_earnings
  FROM (SELECT *, row_number() OVER (PARTITION BY company_id ORDER BY period_end_date DESC) AS n FROM annual) a
  JOIN cpi c ON c.month_date = date_trunc('MONTH', a.period_end_date)
  WHERE n <= 10 GROUP BY company_id
)
SELECT co.company_name, ml.trading_symbol_code, px.price_date, px.price_close, lt.shares_outstanding_count,
       px.price_close * lt.shares_outstanding_count AS market_value,
       lt.trailing_net_income, t.average_real_earnings, t.year_count
FROM members m
JOIN company co ON co.company_id = m.company_id
JOIN main_listing ml ON ml.company_id = m.company_id
JOIN px ON px.listing_id = ml.listing_id
LEFT JOIN latest lt ON lt.company_id = m.company_id
LEFT JOIN ten t ON t.company_id = m.company_id
""")

index_today = spark.sql("""
SELECT count(*) AS member_count,
       count_if(market_value IS NULL) AS missing_market_value_count,
       count_if(average_real_earnings IS NULL) AS missing_earnings_count,
       count_if(year_count < 10) AS fewer_than_10_years_count,
       sum(market_value) / 1e12 AS market_value_trillion,
       sum(trailing_net_income) / 1e9 AS trailing_earnings_billion,
       sum(average_real_earnings) / 1e9 AS average_real_earnings_billion,
       sum(market_value) / sum(trailing_net_income) AS trailing_pe,
       sum(market_value) / sum(average_real_earnings) AS pe_10_year
FROM company_today WHERE market_value IS NOT NULL AND average_real_earnings IS NOT NULL
""")
display(index_today)
r = index_today.first()
summary.append(
    f"Index today: {r.member_count} members used, fewer than 10 years {r.fewer_than_10_years_count}; "
    f"market value {r.market_value_trillion:.2f} tn, trailing earnings {r.trailing_earnings_billion:,.0f} bn, "
    f"10-year average real earnings {r.average_real_earnings_billion:,.0f} bn; "
    f"trailing P/E {r.trailing_pe:.1f}, P/E (10-year) {r.pe_10_year:.1f}"
)
gaps = spark.sql("""SELECT count_if(market_value IS NULL) AS no_mv, count_if(average_real_earnings IS NULL) AS no_earn,
                    count(*) AS all_members FROM company_today""").first()
summary.append(f"Members excluded: no market value {gaps.no_mv}, no 10-K earnings {gaps.no_earn} (of {gaps.all_members})")

top = spark.sql("""
SELECT company_name, trading_symbol_code, round(market_value / 1e9) AS market_value_billion,
       round(average_real_earnings / 1e9, 1) AS average_real_earnings_billion, year_count,
       round(market_value / average_real_earnings, 1) AS pe_10_year
FROM company_today WHERE market_value IS NOT NULL ORDER BY market_value DESC LIMIT 10
""")
display(top)
summary.append("Top 10 by market value: name | symbol | mv bn | avg real earnings bn | years | P/E10")
summary += [f"  {t.company_name} | {t.trading_symbol_code} | {t.market_value_billion} | {t.average_real_earnings_billion} | {t.year_count} | {t.pe_10_year}" for t in top.collect()]
print("\n".join(summary[-12:]))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Share-class check
# MAGIC Companies with more than one listing: the shares SEC reports (cover page) against each listing's price.

# COMMAND ----------

classes = spark.sql("""
SELECT co.company_name, collect_list(l.trading_symbol_code) AS symbols,
       first(f.shares_outstanding_count) AS sec_shares_outstanding_count,
       first(f.concept_used['shares_outstanding_count']) AS concept
FROM listing l
JOIN company co ON co.company_id = l.company_id
JOIN company_fundamentals f ON f.company_id = l.company_id AND f.valid_to_date = DATE '9999-12-31'
GROUP BY co.company_name HAVING count(*) > 1
""")
display(classes)
summary.append("Companies with several listings: name | symbols | SEC shares | concept")
summary += [f"  {c.company_name} | {','.join(c.symbols)} | {num(c.sec_shares_outstanding_count)} | {c.concept}" for c in classes.collect()]
print("\n".join(summary[-10:]))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. History at a few dates (today's members, filings known on each date)

# COMMAND ----------

dates = ["2019-12-31", "2020-03-23", "2021-12-31", "2022-10-12", "2023-12-29", "2024-12-31"]
frames = []
for d in dates:
    frames.append(spark.sql(f"""
    WITH members AS (SELECT company_name, trading_symbol_code FROM company_today),
    ml AS (SELECT l.company_id, l.listing_id FROM listing l JOIN members m ON m.trading_symbol_code = l.trading_symbol_code),
    px AS (
      SELECT ml.company_id, max_by(p.price_close, p.price_date) AS price_close
      FROM price_daily p JOIN ml ON ml.listing_id = p.listing_id
      WHERE p.price_date <= DATE '{d}' AND p.price_date > date_sub(DATE '{d}', 10)
      GROUP BY ml.company_id
    ), known AS (
      SELECT company_id, shares_outstanding_count, net_income AS trailing_net_income
      FROM company_fundamentals WHERE DATE '{d}' BETWEEN valid_from_date AND valid_to_date
    ), cpi_then AS (
      SELECT cpi_value FROM cpi WHERE month_date <= DATE '{d}' ORDER BY month_date DESC LIMIT 1
    ), ten AS (
      SELECT a.company_id, count(*) AS year_count,
             avg(a.net_income * (SELECT cpi_value FROM cpi_then) / c.cpi_value) AS average_real_earnings
      FROM (SELECT *, row_number() OVER (PARTITION BY company_id ORDER BY period_end_date DESC) AS n
            FROM annual WHERE filed_date <= DATE '{d}') a
      JOIN cpi c ON c.month_date = date_trunc('MONTH', a.period_end_date)
      WHERE n <= 10 GROUP BY a.company_id
    )
    SELECT DATE '{d}' AS as_of_date, count(*) AS member_count, count_if(t.year_count < 10) AS fewer_than_10_years_count,
           avg(t.year_count) AS average_year_count,
           sum(px.price_close * k.shares_outstanding_count) / sum(k.trailing_net_income) AS trailing_pe,
           sum(px.price_close * k.shares_outstanding_count) / sum(t.average_real_earnings) AS pe_10_year
    FROM px JOIN known k ON k.company_id = px.company_id JOIN ten t ON t.company_id = px.company_id
    """))
history_df = frames[0]
for f in frames[1:]:
    history_df = history_df.unionByName(f)
display(history_df)
history = history_df.collect()
summary.append("History: date | members | fewer than 10 years | average years | trailing P/E | P/E10")
summary += [f"  {h.as_of_date} | {h.member_count} | {h.fewer_than_10_years_count} | {num(h.average_year_count, '.1f')} | {num(h.trailing_pe, '.1f')} | {num(h.pe_10_year, '.1f')}" for h in history]
print("\n".join(summary[-7:]))

# COMMAND ----------

dbutils.notebook.exit("\n".join(summary))
