"""Builds the Market Climate Genie agent resource from the dashboard's dataset queries (openspec market-climate-genie).

`build()` returns the file content of `resources/genie/market_climate.genie.yml` (JSON, which is YAML), with
`${var.catalog}` left for the bundle to fill in per target. The example SQL is the dashboard's queries, so the
agent and the dashboard give the same figures. `cicd/build_market_climate.py` writes it; a test checks the
committed file equals it.
"""

import hashlib
import json
import re
from pathlib import Path

from common.market_climate_queries import DATASETS

CATALOG = "${var.catalog}"
GOLD = f"{CATALOG}.gold_analytics_gateway"
SILVER = f"{CATALOG}.silver_domain_investments"
INSTRUCTIONS = Path(__file__).with_name("market_climate_genie_instructions.md")
GOLD_TABLES = ["valuation_daily_index_member", "valuation_daily_index", "monitor_daily_signal"]
LITERALS = {":sector_name": "'Information Technology'", ":company_name": "'EQT Corporation'", ":range_code": "'6M'"}

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
}
SAMPLE_QUESTIONS = [
    "What is the market climate today?", "Is the market too expensive right now?", "Which companies push the P/E up most?",
    "Which sector has the highest P/E?", "Why is EQT's P/E so high?",
]
LATEST_SIGNAL = f"(SELECT max(signal_date) FROM {GOLD}.monitor_daily_signal)"
LATEST_MEMBER = f"(SELECT max(valuation_date) FROM {GOLD}.valuation_daily_index_member)"
BENCHMARKS = [
    ("Is the market too expensive right now?",
     f"SELECT lens_name, is_yes, measured_value, threshold_value FROM {GOLD}.monitor_daily_signal "
     f"WHERE signal_code = 'too_expensive' AND signal_date = {LATEST_SIGNAL} ORDER BY lens_code"),
    ("Which sector has the highest P/E?",
     f"SELECT c.gics_sector_name, sum(m.market_value_amount) / sum(m.earnings_ten_year_average_inflation_adjusted_amount) AS sector_pe "
     f"FROM {GOLD}.valuation_daily_index_member m JOIN {SILVER}.company c ON c.company_id = m.company_id "
     f"WHERE m.is_used AND m.valuation_date = {LATEST_MEMBER} GROUP BY c.gics_sector_name "
     f"HAVING sum(m.earnings_ten_year_average_inflation_adjusted_amount) > 0 ORDER BY sector_pe DESC LIMIT 1"),
    ("Why is EQT's P/E so high?",
     f"SELECT m.price_earnings_ten_year_average_inflation_adjusted_ratio, m.market_value_amount / m.earnings_trailing_twelve_months_amount AS pe_trailing, "
     f"m.earnings_trailing_twelve_months_amount, m.earnings_ten_year_average_inflation_adjusted_amount "
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
        {"identifier": index},
        {"identifier": members},
        {"identifier": signal, "column_configs": [entity("lens_name"), entity("signal_name")]},
    ]
    return {
        "version": 2,
        "config": {"sample_questions": by_id([{"id": identifier("sample:" + q), "question": [q]} for q in SAMPLE_QUESTIONS])},
        "data_sources": {"tables": sorted(tables, key=lambda table: table["identifier"])},
        "instructions": {
            "text_instructions": [{"id": identifier("instructions"), "content": INSTRUCTIONS.read_text(encoding="utf-8").strip().splitlines()}],
            "example_question_sqls": by_id([
                {"id": identifier("example:" + name), "question": [question], "sql": [for_genie(DATASETS[name][1])], "usage_guidance": [guidance]}
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
        "title": "Market Climate",
        "description": "Ask about the market climate lights, the S&P 500 price/earnings ratio and its members.",
        "warehouse_id": "${var.warehouse_id}",
        "parent_path": "${workspace.resource_path}",
        "serialized_space": space(),
        "permissions": [{"group_name": "users", "level": "CAN_RUN"}],
    }}}}
    return json.dumps(resource, indent=2) + "\n"
