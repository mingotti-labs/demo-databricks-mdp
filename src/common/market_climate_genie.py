"""Builds the Market Climate Genie agent resource from the dashboard's dataset queries (openspec market-climate-genie).

`build()` returns the file content of `resources/genie/market_climate.genie.yml` (JSON, which is YAML), with
`${var.catalog}` left for the bundle to fill in per target. The example SQL is the dashboard's queries, so the
agent and the dashboard give the same figures. `cicd/build_dashboards.py` writes it; a test checks the
committed file equals it.
"""

import hashlib
import json
import re
from pathlib import Path

from common.currency_queries import DATASETS as CURRENCY_DATASETS
from common.inflation_queries import DATASETS as INFLATION_DATASETS
from common.market_climate_queries import DATASETS

CATALOG = "${var.catalog}"
GOLD = f"{CATALOG}.gold_analytics_gateway"
SILVER = f"{CATALOG}.silver_domain_investments"
INSTRUCTIONS = Path(__file__).with_name("market_climate_genie_instructions.md")
GOLD_TABLES = ["valuation_daily_index_member", "valuation_daily_index", "monitor_daily_signal"]
LITERALS = {
    ":sector_name": "'Information Technology'",
    ":company_name": "'EQT Corporation'",
    ":range_code": "'6M'",
    ":currency_code": "'CHF'",
}

EXAMPLES = {
    "ds_lights": ("What is the market climate today?", "Both lights with the yes count and the climate date."),
    "ds_answers": ("What are the three answers of each climate today, and why?", "One row per climate and question."),
    "ds_light_history": ("How have the lights changed over time?", "Yes answers per day for each climate, last 36 months."),
    "ds_index_day": ("What is the S&P 500 P/E today, on 10-year inflation-adjusted and on trailing earnings?", "Index row of the latest day."),
    "ds_pe_history": ("How has the S&P 500 P/E moved over time?", "Both measures per day, last 36 months."),
    "ds_top_up": ("Which companies push the index P/E up most?", "Top 10 of the latest day."),
    "ds_top_down": ("Which companies push the index P/E down most?", "Top 10 of the latest day."),
    "ds_excluded": ("Which members are left out today, and why?", "Members that are not used, with the reason."),
    "ds_checks": ("Do the member rows add up to the index row?", "Differences should be 0."),
    "ds_sectors": ("What is the P/E of each sector, and the index P/E without it?", "Sectors of the latest day."),
    "ds_company_check": ("How is EQT's P/E worked out, step by step?", "Replace 'EQT Corporation' with the company asked about."),
    "ds_company_figures": ("What are EQT's last close and its 52-week high and low?", "Replace 'EQT Corporation' with the company asked about."),
    "ds_freshness": ("How fresh is the data?", "The climate date and the latest date of each input."),
    "ds_rating": ("What is the inflation rating today?", "Rating row of the latest day: stars on, label, US consumer prices over 12 months."),
    "ds_stars": ("Which inflation stars are on today, and why?", "One row per vehicle; On means it points to inflation."),
    "ds_rating_history": ("How has the inflation rating changed over time?", "Rating per day, last 36 months."),
    "ds_commodities": ("How do the commodity benchmarks compare with their 200-day averages today?", "Eight benchmarks; only the CRB index and gold vote."),
    "ds_real_rate_history": ("What is the real interest rate over time?", "Effective rate minus the US consumer price change over 12 months, last 36 months."),
    "ds_cpi_changes": ("How have US consumer prices changed over 12 months?", "The 12-month change and the change against the previous reading, last 36 months."),
    "ds_rate_history": ("What is the short-term interest rate and its 200-day average?", "Federal funds effective rate, last 36 months."),
    "ds_inflation_freshness": ("How fresh is the inflation data?", "The rating date and the latest date of each input."),
    "ds_dollar": ("Is the dollar strong or weak today?", "The US Dollar Index (megatrend) and the Federal Reserve broad dollar index against their 200-day averages."),
    "ds_currency_grid": ("Which currencies are gaining or losing against the US dollar and the Australian dollar today?", "One row per currency; value, distance from the 200-day average and Gaining or Losing against each base."),
    "ds_country_rates": ("What are the short-term interest rates and 10-year yields of the main countries?", "Each reading with its date; a note says when a reading is older than 4 months."),
    "ds_currency_history": ("How has the Swiss franc moved against the US and Australian dollars?", "Replace 'CHF' with the currency code asked about (USD, EUR, JPY, GBP, CHF, CAD, SEK, AUD, NZD, CNY)."),
    "ds_currency_rates_history": ("How have Switzerland's interest rates changed?", "Replace 'CHF' with the currency code of the country asked about."),
    "ds_dollar_history": ("How have the dollar indexes moved over time?", "Both indexes and their 200-day averages, last 36 months."),
}
QUERIES = {**DATASETS, **INFLATION_DATASETS, **CURRENCY_DATASETS}
SAMPLE_QUESTIONS = [
    "What is the market climate today?", "Is the market too expensive right now?", "Which companies push the P/E up most?",
    "Which sector has the highest P/E?", "Why is EQT's P/E so high?", "What is the inflation rating today?",
    "Which currencies are gaining against the Australian dollar?",
]
LATEST_SIGNAL = f"(SELECT max(signal_date) FROM {GOLD}.monitor_daily_signal)"
LATEST_MEMBER = f"(SELECT max(valuation_date) FROM {GOLD}.valuation_daily_index_member)"
LATEST_CURRENCY = f"(SELECT max(signal_date) FROM {GOLD}.monitor_daily_signal WHERE monitor_code = 'currency')"
LATEST_INFLATION = f"(SELECT max(signal_date) FROM {GOLD}.monitor_daily_signal WHERE monitor_code = 'inflation_deflation')"
BENCHMARKS = [
    ("Is the market too expensive right now?",
     f"SELECT lens_name, is_yes, measured_value, threshold_value FROM {GOLD}.monitor_daily_signal "
     f"WHERE signal_code = 'too_expensive' AND signal_date = {LATEST_SIGNAL} ORDER BY lens_code"),
    ("Which sector has the highest P/E?",
     f"SELECT c.gics_sector_name, sum(m.market_value_amount) / sum(m.earnings_ten_year_average_inflation_adjusted_amount) AS sector_pe "
     f"FROM {GOLD}.valuation_daily_index_member m JOIN {SILVER}.company c ON c.company_id = m.company_id "
     f"WHERE m.is_used AND m.valuation_date = {LATEST_MEMBER} GROUP BY c.gics_sector_name "
     f"HAVING sum(m.earnings_ten_year_average_inflation_adjusted_amount) > 0 ORDER BY sector_pe DESC LIMIT 1"),
    ("What are EQT's P/E on trailing earnings and on 10-year inflation-adjusted earnings?",
     f"SELECT m.market_value_amount / m.earnings_trailing_twelve_months_amount AS pe_trailing, "
     f"m.price_earnings_ten_year_average_inflation_adjusted_ratio AS pe_ten_year_adjusted "
     f"FROM {GOLD}.valuation_daily_index_member m JOIN {SILVER}.company c ON c.company_id = m.company_id "
     f"WHERE c.company_name = 'EQT Corporation' AND m.valuation_date = {LATEST_MEMBER}"),
    ("Is the Fed in the way?",
     f"SELECT lens_name, is_yes, reason_text FROM {GOLD}.monitor_daily_signal "
     f"WHERE signal_code = 'fed_in_the_way' AND signal_date = {LATEST_SIGNAL} ORDER BY lens_code"),
    ("How many members are left out today?",
     f"SELECT count(*) AS members_left_out FROM {GOLD}.valuation_daily_index_member "
     f"WHERE NOT is_used AND valuation_date = {LATEST_MEMBER}"),
    ("What did the long-run light say on 2026-10-01?",
     f"SELECT band_code, yes_count, action_name FROM {GOLD}.monitor_daily_signal "
     f"WHERE signal_code = 'climate' AND lens_code = 'long_run' AND signal_date = DATE '2026-10-01'"),
    ("How many inflation stars are on today?",
     f"SELECT yes_count FROM {GOLD}.monitor_daily_signal WHERE monitor_code = 'inflation_deflation' "
     f"AND signal_code = 'rating' AND signal_date = {LATEST_INFLATION}"),
    ("What is the real interest rate today?",
     f"SELECT rate_value FROM {SILVER}.market_rate_indicator_daily WHERE rate_code = 'us_real_federal_funds_rate' "
     f"AND indicator_date = (SELECT max(indicator_date) FROM {SILVER}.market_rate_indicator_daily WHERE rate_code = 'us_real_federal_funds_rate')"),
    ("When was the last deflation rating?",
     f"SELECT max(signal_date) FROM {GOLD}.monitor_daily_signal WHERE monitor_code = 'inflation_deflation' "
     f"AND signal_code = 'rating' AND measured_value = -1"),
    ("Is the dollar strong or weak today?",
     f"SELECT signal_name, is_yes FROM {GOLD}.monitor_daily_signal WHERE monitor_code = 'currency' "
     f"AND signal_code IN ('dollar_index', 'dollar_broad_index') AND signal_date = {LATEST_CURRENCY} ORDER BY signal_code"),
    ("Which currencies are gaining against the Australian dollar today?",
     f"SELECT signal_name FROM {GOLD}.monitor_daily_signal WHERE monitor_code = 'currency' AND lens_code = 'australian_dollar' "
     f"AND signal_code <> 'summary' AND is_yes AND signal_date = {LATEST_CURRENCY} ORDER BY signal_name"),
    ("What is Japan's short-term interest rate?",
     f"SELECT rate_value, observation_date FROM {SILVER}.market_rate_daily WHERE rate_code = 'japan_3_month_interbank_rate' "
     f"ORDER BY observation_date DESC LIMIT 1"),
]


def identifier(text: str) -> str:
    """A stable 32-hex id, so rebuilding changes nothing."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def for_genie(query: str) -> str:
    """The dashboard query with full table names and today's date instead of its parameters."""
    query = query.replace("coalesce(:as_of_date, DATE '9999-12-31')", "current_date()")
    for parameter, literal in LITERALS.items():
        query = query.replace(parameter, literal)
    query = re.sub(r"(?<![.\w])(%s)\b" % "|".join(GOLD_TABLES), rf"{GOLD}.\1", query)
    return re.sub(r"(?<![.\w])silver_domain_investments\.", f"{SILVER}.", query).strip()


def by_id(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda item: item["id"])


def join_spec(left: str, right: str, condition: str, relationship: str) -> dict:
    return {"id": identifier(f"join:{left}:{right}"), "left": {"identifier": left, "alias": left.rsplit(".", 1)[1]},
            "right": {"identifier": right, "alias": right.rsplit(".", 1)[1]},
            "sql": [condition, f"--rt=FROM_RELATIONSHIP_TYPE_{relationship}--"]}


def space() -> dict:
    members, index, signal = (f"{GOLD}.{name}" for name in GOLD_TABLES)
    company, price = f"{SILVER}.company", f"{SILVER}.price_daily"
    entity = lambda name: {"column_name": name, "enable_entity_matching": True, "enable_format_assistance": True}  # noqa: E731
    tables = [
        {"identifier": company, "column_configs": [entity("company_name"), entity("gics_sector_name")]},
        {"identifier": price},
        {"identifier": f"{SILVER}.market_rate_daily"},
        {"identifier": f"{SILVER}.market_rate_indicator_daily"},
        {"identifier": f"{SILVER}.price_indicator_daily"},
        {"identifier": index},
        {"identifier": members},
        {"identifier": signal, "column_configs": [entity("lens_name"), entity("signal_name")]},
    ]
    return {
        "version": 2,
        "config": {"sample_questions": by_id([{"id": identifier("sample:" + q), "question": [q]} for q in SAMPLE_QUESTIONS])},
        "data_sources": {"tables": sorted(tables, key=lambda table: table["identifier"])},
        "instructions": {
            "text_instructions": [{"id": identifier("instructions"), "content": [line + chr(10) for line in INSTRUCTIONS.read_text(encoding="utf-8").strip().splitlines()]}],
            "example_question_sqls": by_id([
                {"id": identifier("example:" + name), "question": [question], "sql": [for_genie(QUERIES[name][1])], "usage_guidance": [guidance]}
                for name, (question, guidance) in EXAMPLES.items()]),
            "join_specs": by_id([
                join_spec(members, company, "`valuation_daily_index_member`.`company_id` = `company`.`company_id`", "MANY_TO_ONE"),
                join_spec(members, index, "`valuation_daily_index_member`.`index_code` = `valuation_daily_index`.`index_code` "
                                         "AND `valuation_daily_index_member`.`valuation_date` = `valuation_daily_index`.`valuation_date`", "MANY_TO_ONE"),
                join_spec(members, price, "`valuation_daily_index_member`.`listing_id` = `price_daily`.`listing_id`", "ONE_TO_MANY"),
            ]),
        },
        "benchmarks": {"questions": by_id([
            {"id": identifier("benchmark:" + question), "question": [question], "answer": [{"format": "SQL", "content": [sql]}]}
            for question, sql in BENCHMARKS])},
    }


def build() -> str:
    resource = {"resources": {"genie_spaces": {"market_climate_genie": {
        "title": "Investment Intelligence",
        "description": "Ask about the market climate lights, the inflation/deflation rating, the S&P 500 price/earnings ratio and its members.",
        "warehouse_id": "${var.warehouse_id}",
        "parent_path": "${workspace.resource_path}",
        "serialized_space": space(),
        "permissions": [{"group_name": "users", "level": "CAN_RUN"}],
    }}}}
    return json.dumps(resource, indent=2) + "\n"
