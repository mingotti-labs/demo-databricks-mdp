# Silver Domain investments, part 3: company fundamentals as known on each filing
# date (point in time), from SEC facts (openspec silver-domain-investments).
# One row per company and 10-K, 10-K/A, 10-Q or 10-Q/A filing; valid_from_date is
# the filing date, valid_to_date the day before the next one. Balance sheet figures
# are the filing's own at its period end; income and cash flow figures are trailing
# twelve months (a 10-K's year, or for a 10-Q the latest annual value plus this
# year-to-date minus the prior year-to-date). Periods are told apart by start and
# end, never by SEC's fy, which also labels comparatives.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.investments import (  # noqa: E402
    COMPANY_FUNDAMENTALS_COMMENTS,
    FAR_FUTURE_DATE,
    IDENTIFIER_SOURCE,
    US_CPI_SERIES_ID,
    entity_id_sql,
    figure_columns_sql,
    figure_names,
    figure_values_sql,
    schema_with_comments,
)

LANDING = "silver_landing"
PASS_THROUGH = [f for f in figure_names() if f != "total_liabilities"]
FIGURE_SELECT = ",\n               ".join(f"w.{f}" for f in PASS_THROUGH)

FILINGS = f"""
WITH figures AS (
  SELECT * FROM VALUES {figure_values_sql()} AS figures(figure, kind, unit)
), mapping AS (
  SELECT figure, taxonomy, concept, CAST(priority AS INT) AS priority
  FROM {LANDING}.portfolio__concept_mapping WHERE is_current
), predecessors AS (
  SELECT predecessor_cik, cik AS successor_cik
  FROM {LANDING}.portfolio__predecessor_ciks WHERE is_current
), mapped AS (
  SELECT f.cik, coalesce(pc.successor_cik, f.cik) AS entity_cik, f.accn, f.form,
         to_date(f.filed) AS filed, to_date(f.start) AS start_date, to_date(f.end) AS end_date, CAST(f.val AS DECIMAL(28, 6)) AS value, f.ingested_timestamp,
         m.figure, m.priority, m.concept, g.kind
  FROM {LANDING}.sec__company_facts f
  JOIN mapping m ON m.taxonomy = f.taxonomy AND m.concept = f.concept
  JOIN figures g ON g.figure = m.figure AND g.unit = f.unit
  LEFT JOIN predecessors pc ON pc.predecessor_cik = f.cik
  WHERE f.is_current AND f.form IN ('10-K', '10-K/A', '10-Q', '10-Q/A')
), filings AS (
  SELECT cik, accn, max(form) AS form, max(filed) AS filed, max(end_date) AS period_end,
         min(ingested_timestamp) AS ingested_timestamp
  FROM mapped WHERE kind NOT IN ('cover', 'period') GROUP BY cik, accn
), instant AS (
  SELECT cik, accn, figure, value, concept FROM (
    SELECT m.cik, m.accn, m.figure, m.value, m.concept,
           row_number() OVER (PARTITION BY m.cik, m.accn, m.figure ORDER BY m.priority) AS pick
    FROM mapped m JOIN filings fl ON fl.cik = m.cik AND fl.accn = m.accn
    WHERE m.kind = 'instant' AND m.end_date = fl.period_end
  ) WHERE pick = 1
), cover AS (
  SELECT cik, accn, figure, value, concept FROM (
    SELECT cik, accn, figure, value, concept,
           row_number() OVER (PARTITION BY cik, accn, figure ORDER BY priority, end_date DESC) AS pick
    FROM mapped WHERE kind = 'cover'
  ) WHERE pick = 1
), period AS (
  SELECT cik, accn, figure, value, concept FROM (
    SELECT m.cik, m.accn, m.figure, m.value, m.concept,
           row_number() OVER (
             PARTITION BY m.cik, m.accn, m.figure ORDER BY m.priority, datediff(m.end_date, m.start_date)
           ) AS pick
    FROM mapped m JOIN filings fl ON fl.cik = m.cik AND fl.accn = m.accn
    WHERE m.kind = 'period' AND m.end_date = fl.period_end
  ) WHERE pick = 1
), annual AS (
  SELECT cik, entity_cik, accn, figure, priority, concept, filed, end_date, value
  FROM mapped
  WHERE kind = 'duration' AND form LIKE '10-K%' AND datediff(end_date, start_date) BETWEEN 330 AND 380
), yearly AS (
  SELECT a.cik, a.accn, a.figure, a.priority, a.concept, a.value
  FROM annual a JOIN filings fl ON fl.cik = a.cik AND fl.accn = a.accn AND a.end_date = fl.period_end
), year_to_date AS (
  SELECT cik, entity_cik, accn, figure, priority, concept, period_end, filed, value, days FROM (
    SELECT m.cik, m.entity_cik, m.accn, m.figure, m.priority, m.concept, fl.period_end, fl.filed, m.value,
           datediff(m.end_date, m.start_date) AS days,
           row_number() OVER (
             PARTITION BY m.cik, m.accn, m.figure, m.concept ORDER BY datediff(m.end_date, m.start_date) DESC
           ) AS pick
    FROM mapped m JOIN filings fl ON fl.cik = m.cik AND fl.accn = m.accn
    WHERE m.kind = 'duration' AND fl.form LIKE '10-Q%' AND m.end_date = fl.period_end
      AND datediff(m.end_date, m.start_date) < 300
  ) WHERE pick = 1
), prior_year AS (
  SELECT cik, entity_cik, accn, figure, priority, concept, period_end, filed, value, prior_value FROM (
    SELECT y.cik, y.entity_cik, y.accn, y.figure, y.priority, y.concept, y.period_end, y.filed, y.value,
           p.value AS prior_value,
           row_number() OVER (
             PARTITION BY y.cik, y.accn, y.figure, y.concept
             ORDER BY abs(datediff(p.end_date, p.start_date) - y.days), p.end_date DESC
           ) AS pick
    FROM year_to_date y
    JOIN mapped p ON p.cik = y.cik AND p.accn = y.accn AND p.concept = y.concept
     AND p.kind = 'duration'
     AND p.end_date BETWEEN date_sub(y.period_end, 372) AND date_sub(y.period_end, 358)
     AND abs(datediff(p.end_date, p.start_date) - y.days) <= 10
  ) WHERE pick = 1
), quarterly AS (
  SELECT cik, accn, figure, priority, concept, value FROM (
    SELECT y.cik, y.accn, y.figure, y.priority, y.concept,
           a.value + y.value - y.prior_value AS value,
           row_number() OVER (
             PARTITION BY y.cik, y.accn, y.figure, y.concept ORDER BY a.end_date DESC, a.filed DESC
           ) AS pick
    FROM prior_year y
    JOIN annual a ON a.entity_cik = y.entity_cik AND a.figure = y.figure AND a.concept = y.concept
     AND a.filed <= y.filed AND a.end_date < y.period_end
  ) WHERE pick = 1
), duration AS (
  SELECT cik, accn, figure, value, concept FROM (
    SELECT cik, accn, figure, value, concept,
           row_number() OVER (PARTITION BY cik, accn, figure ORDER BY priority) AS pick
    FROM (
      SELECT cik, accn, figure, priority, concept, value FROM yearly
      UNION ALL
      SELECT cik, accn, figure, priority, concept, value FROM quarterly
    )
  ) WHERE pick = 1
), chosen AS (
  SELECT cik, accn, figure, value, concept FROM instant
  UNION ALL SELECT cik, accn, figure, value, concept FROM cover
  UNION ALL SELECT cik, accn, figure, value, concept FROM period
  UNION ALL SELECT cik, accn, figure, value, concept FROM duration
), wide AS (
  SELECT cik, accn,
         {figure_columns_sql()},
         map_from_entries(collect_list(struct(figure, concept))) AS concept_used
  FROM chosen GROUP BY cik, accn
), first_filing AS (
  SELECT cik, min(filed) AS first_filed FROM filings GROUP BY cik
), relabelled AS (
  SELECT coalesce(p.successor_cik, fl.cik) AS central_index_key,
         fl.cik, fl.accn, fl.form, fl.filed, fl.period_end, fl.ingested_timestamp
  FROM filings fl
  LEFT JOIN predecessors p ON p.predecessor_cik = fl.cik
  LEFT JOIN first_filing ff ON ff.cik = p.successor_cik
  WHERE p.predecessor_cik IS NULL OR ff.first_filed IS NULL OR fl.filed < ff.first_filed
), one_per_day AS (
  SELECT * FROM (
    SELECT *, row_number() OVER (PARTITION BY central_index_key, filed ORDER BY accn DESC) AS pick
    FROM relabelled
  ) WHERE pick = 1
), base AS (
  SELECT {entity_id_sql(f"'{IDENTIFIER_SOURCE}'", "r.central_index_key")} AS company_id,
         r.central_index_key,
         r.filed AS valid_from_date,
         coalesce(
           date_sub(lead(r.filed) OVER (PARTITION BY r.central_index_key ORDER BY r.filed), 1),
           DATE '{FAR_FUTURE_DATE}'
         ) AS valid_to_date,
         r.form AS form_code,
         r.accn AS accession_number,
         r.period_end AS period_end_date,
         'USD' AS currency_code,
         {FIGURE_SELECT},
         coalesce(w.total_liabilities, w.liabilities_and_equity - w.total_equity) AS total_liabilities,
         w.operating_cash_flow - w.capex AS free_cash_flow,
         CASE WHEN w.long_term_debt IS NULL AND w.short_term_debt IS NULL THEN NULL
              ELSE coalesce(w.long_term_debt, 0) + coalesce(w.short_term_debt, 0) END AS total_debt,
         w.operating_income + w.depreciation_and_amortisation_amount
           AS earnings_before_interest_tax_depreciation_amortisation,
         CASE WHEN w.total_liabilities IS NULL
               AND w.liabilities_and_equity IS NOT NULL AND w.total_equity IS NOT NULL
              THEN map_concat(w.concept_used, map('total_liabilities', 'derived'))
              ELSE w.concept_used END AS concept_used,
         r.ingested_timestamp
  FROM one_per_day r
  JOIN wide w ON w.cik = r.cik AND w.accn = r.accn
), annual_filings AS (
  SELECT company_id, valid_from_date AS filed_date, period_end_date, net_income
  FROM base WHERE form_code LIKE '10-K%' AND net_income IS NOT NULL
), known_years AS (
  SELECT b.company_id, b.valid_from_date, a.period_end_date, a.net_income,
         row_number() OVER (
           PARTITION BY b.company_id, b.valid_from_date, a.period_end_date ORDER BY a.filed_date DESC
         ) AS version_rank
  FROM base b JOIN annual_filings a ON a.company_id = b.company_id AND a.filed_date <= b.valid_from_date
), last_years AS (
  SELECT company_id, valid_from_date, period_end_date, net_income FROM (
    SELECT *, row_number() OVER (
             PARTITION BY company_id, valid_from_date ORDER BY period_end_date DESC
           ) AS year_rank
    FROM known_years WHERE version_rank = 1
  ) WHERE year_rank <= 10
), cpi_months AS (
  SELECT observation_date AS month_date, CAST(value AS DECIMAL(18, 6)) AS cpi_value
  FROM {LANDING}.fred__observations
  WHERE series_id = '{US_CPI_SERIES_ID}' AND try_cast(value AS DECIMAL(18, 6)) IS NOT NULL
), cpi_at AS (
  SELECT period_end_date, cpi_value FROM (
    SELECT d.period_end_date, c.cpi_value,
           row_number() OVER (PARTITION BY d.period_end_date ORDER BY c.month_date DESC) AS pick
    FROM (SELECT DISTINCT period_end_date FROM base) d
    JOIN cpi_months c ON c.month_date <= d.period_end_date
  ) WHERE pick = 1
), ten_year AS (
  SELECT y.company_id, y.valid_from_date,
         count(*) AS earnings_year_count,
         CAST(avg(y.net_income) AS DECIMAL(28, 6)) AS earnings_ten_year_average_amount,
         CAST(avg(y.net_income * current_cpi.cpi_value / year_cpi.cpi_value) AS DECIMAL(28, 6))
           AS earnings_ten_year_average_inflation_adjusted_amount
  FROM last_years y
  JOIN base b ON b.company_id = y.company_id AND b.valid_from_date = y.valid_from_date
  LEFT JOIN cpi_at current_cpi ON current_cpi.period_end_date = b.period_end_date
  LEFT JOIN cpi_at year_cpi ON year_cpi.period_end_date = y.period_end_date
  GROUP BY y.company_id, y.valid_from_date
)
SELECT b.*,
       cpi.cpi_value AS consumer_price_index_value,
       t.earnings_year_count,
       t.earnings_ten_year_average_amount,
       t.earnings_ten_year_average_inflation_adjusted_amount
FROM base b
LEFT JOIN cpi_at cpi ON cpi.period_end_date = b.period_end_date
LEFT JOIN ten_year t ON t.company_id = b.company_id AND t.valid_from_date = b.valid_from_date
"""


COLUMNS = [(field.name, field.dataType.simpleString()) for field in spark.sql(FILINGS).schema.fields]


@dp.materialized_view(
    comment="Company fundamentals as reported on each 10-K or 10-Q filing date. Income and cash "
    "flow figures are trailing twelve months; valid_from_date and valid_to_date give the range "
    "the row was the latest known. The 10-year earnings averages roll one fiscal year per 10-K.",
    schema=schema_with_comments(COLUMNS, COMPANY_FUNDAMENTALS_COMMENTS),
)
def company_fundamentals():
    return spark.sql(FILINGS)
