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
from common.strategy_queries import DATASETS as STRATEGY_DATASETS

CATALOG = "${var.catalog}"
GOLD = f"{CATALOG}.gold_analytics_gateway"
SILVER = f"{CATALOG}.silver_domain_investments"
INSTRUCTIONS = Path(__file__).with_name("market_climate_genie_instructions.md")
GOLD_TABLES = ["valuation_daily_index_member", "valuation_daily_index", "monitor_daily_signal", "strategy_daily_event"]
LITERALS = {
    ":sector_name": "'Information Technology'",
    ":company_name": "'EQT Corporation'",
    ":range_code": "'6M'",
    ":history_range_code": "'36M'",
    ":currency_code": "'CHF'",
    ":base_code": "'AUD'",
    ":fund_code": "'SQQQ'",
    ":setup_period": "'all'",
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
    "ds_yield_ranking": ("Which country can deliver the highest yield, considering its interest rate and its currency's change, in a table ranking?", "Short-term rate plus the 12-month change of the currency against the base; replace 'AUD' with 'USD' for a US dollar base. Backward-looking."),
    "ds_us_yield_curve": ("How does the US 10-year Treasury yield compare with the 3-month, 1-year, 2-year and 3-year yields?", "One row per day and short-term maturity: both yields and the gap (10-year minus the short-term one, percentage points) over the last 36 months."),
    "ds_bear_week": ("Is the bear market fund setup on, and is there an entry this week?", "GO or NO GO for the latest complete week, the S&P 500 week change, the entry band and what to do."),
    "ds_bear_checks": ("What are the checks behind the bear market fund setup, entry and exit?", "Eight rows: the two setup checks, three entry bands and three exit checks of the latest complete week."),
    "ds_bear_funds": ("How are the bear funds doing?", "SQQQ, PSQ, SH, SDS and SPXU: last close and the change over 5 trading days."),
    "ds_bear_period_events": ("What happened in the bear market fund setup periods?", "Events of every setup period; replace 'all' with a setup start date to see one period."),
    "ds_fund_chart": ("How has the bear fund SQQQ moved against the S&P 500, and when was the setup on?", "Daily fund close, S&P 500 close, whether the day is in a setup period and the entry days; replace 'SQQQ' with another bear fund."),
    "ds_short_gate": ("Is the market climate red, so that short selling can run?", "The lights of the latest climate day and the gate."),
    "ds_short_candidates": ("Which stocks are short selling candidates this week?", "Open setup periods of the latest complete week: price-to-sales, weeks down, setup and entry lights."),
    "ds_short_events": ("What are the latest short selling events?", "The 40 latest setup starts, entries and setup ends."),
    "ds_efficient_summary": ("How many stocks pass the efficient stocks screen today?", "Members screened and passing on the latest S&P 500 trading day, and the highest tr60."),
    "ds_efficient_closest": ("Which stocks are closest to passing the efficient stocks screen?", "The 20 members with the highest tr60: tr60, r60 (information only), 60-day change, average range and true range, average volume and the lights."),
}
QUERIES = {**DATASETS, **INFLATION_DATASETS, **CURRENCY_DATASETS, **STRATEGY_DATASETS}
SAMPLE_QUESTIONS = [
    "What is the market climate today?", "Is the market too expensive right now?", "Which companies push the P/E up most?",
    "Which sector has the highest P/E?", "Why is EQT's P/E so high?", "What is the inflation rating today?",
    "Which currencies are gaining against the Australian dollar?", "Rank the countries by interest rate and currency change.",
    "Is the bear market fund setup on?", "Which stocks are short selling candidates this week?",
    "Which stocks are closest to passing the efficient stocks screen?",
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
    ("When did the bear market fund setup last start?",
     f"SELECT max(event_date) AS last_setup_start FROM {GOLD}.strategy_daily_event "
     f"WHERE strategy_code = 'bear_market_fund' AND event_code = 'setup_start'"),
    ("Which strategy entries fired in the last 6 months?",
     f"SELECT strategy_name, trading_symbol_code, event_date FROM {GOLD}.strategy_daily_event "
     f"WHERE event_code = 'entry' AND event_date >= add_months(current_date(), -6) ORDER BY event_date, trading_symbol_code"),
    ("Is the dollar strong or weak today?",
     f"SELECT signal_name, CASE WHEN is_yes THEN 'Strong' ELSE 'Weak' END AS dollar_state FROM {GOLD}.monitor_daily_signal WHERE monitor_code = 'currency' "
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


def extra_benchmarks() -> list[tuple[str, str]]:
    """Benchmarks built from the dashboard's own query, so the expected answer follows it."""
    ranking = for_genie(QUERIES["ds_yield_ranking"][1])
    candidates = for_genie(QUERIES["ds_short_candidates"][1])
    bear_week = for_genie(QUERIES["ds_bear_week"][1])
    closest = for_genie(QUERIES["ds_efficient_closest"][1])
    return [(
        "Which country has the highest short-term rate plus 12-month currency change against the Australian dollar?",
        f"SELECT currency_name, short_plus_12m FROM ({ranking}) WHERE rank_position = 1",
    ), (
        "Is the bear market fund setup on?",
        f"SELECT setup_text FROM ({bear_week})",
    ), (
        "Which stocks are short selling candidates this week?",
        f"SELECT trading_symbol_code FROM ({candidates}) ORDER BY trading_symbol_code",
    ), (
        "Which stocks are closest to passing the efficient stocks screen?",
        f"SELECT trading_symbol_code FROM ({closest}) ORDER BY efficiency_tr60_ratio DESC",
    )]


def space() -> dict:
    members, index, signal = (f"{GOLD}.{name}" for name in GOLD_TABLES[:3])
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
        {"identifier": f"{GOLD}.strategy_daily_event",
         "column_configs": [entity("event_name"), entity("strategy_name"), entity("trading_symbol_code")]},
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
            for question, sql in BENCHMARKS + extra_benchmarks()])},
    }


def build() -> str:
    resource = {"resources": {"genie_spaces": {"market_climate_genie": {
        "title": "Investment Intelligence",
        "description": "Ask about the market climate lights, the inflation/deflation rating, the currencies, the S&P 500 price/earnings ratio and its members, and the bear market fund and short selling strategies.",
        "warehouse_id": "${var.warehouse_id}",
        "parent_path": "${workspace.resource_path}",
        "serialized_space": space(),
        "permissions": [{"group_name": "users", "level": "CAN_RUN"}],
    }}}}
    return json.dumps(resource, indent=2) + "\n"
