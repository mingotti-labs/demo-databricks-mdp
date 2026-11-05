import json
from pathlib import Path

from common import market_climate_dashboard, market_climate_genie

ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_file_equals_its_builder():
    committed = (ROOT / "src" / "dashboards" / "market_climate.lvdash.json").read_text(encoding="utf-8")
    assert committed.replace("\r\n", "\n") == market_climate_dashboard.build()


def test_every_dataset_has_a_title_and_query():
    for dataset in json.loads(market_climate_dashboard.build())["datasets"]:
        assert dataset["displayName"] and dataset["queryLines"][0].strip()


def test_genie_file_equals_its_builder():
    committed = (ROOT / "resources" / "genie" / "market_climate.genie.yml").read_text(encoding="utf-8")
    assert committed.replace("\r\n", "\n") == market_climate_genie.build()


def test_genie_lists_are_sorted_and_ids_unique():
    space = json.loads(market_climate_genie.build())["resources"]["genie_spaces"]["market_climate_genie"]["serialized_space"]
    ids = []
    for items in (space["config"]["sample_questions"], space["instructions"]["example_question_sqls"],
                  space["instructions"]["join_specs"], space["benchmarks"]["questions"], space["instructions"]["text_instructions"]):
        assert [i["id"] for i in items] == sorted(i["id"] for i in items)
        ids += [i["id"] for i in items]
    assert len(ids) == len(set(ids))
    identifiers = [t["identifier"] for t in space["data_sources"]["tables"]]
    assert identifiers == sorted(identifiers)


def test_genie_examples_name_the_catalog_and_no_parameters():
    space = json.loads(market_climate_genie.build())["resources"]["genie_spaces"]["market_climate_genie"]["serialized_space"]
    for example in space["instructions"]["example_question_sqls"]:
        sql = example["sql"][0]
        assert ":as_of_date" not in sql and ":sector_name" not in sql and ":company_name" not in sql and ":range_code" not in sql
        assert "${var.catalog}.gold_analytics_gateway." in sql or "${var.catalog}.silver_domain_investments." in sql
        assert " FROM monitor_daily_signal" not in sql and " JOIN silver_domain_investments." not in sql
