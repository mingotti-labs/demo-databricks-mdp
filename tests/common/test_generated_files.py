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


def test_climate_page_history_charts_follow_the_range_filter():
    dashboard = json.loads(market_climate_dashboard.build())
    history = ["ds_light_history", "ds_pe_history", "ds_fed_history", "ds_trend_history"]
    datasets = {d["name"]: d for d in dashboard["datasets"]}
    for name in history:
        assert "range_start_date" in datasets[name]["queryLines"][0]
        assert datasets[name]["parameters"][0]["keyword"] == "history_range_code"
    first_page = dashboard["pages"][0]["layout"]
    filter_widget = next(w["widget"] for w in first_page if w["widget"]["name"] == "filter-history-range")
    assert {q["query"]["datasetName"] for q in filter_widget["queries"]} == {"ds_history_range_options", *history}
    charts = [w["widget"] for w in first_page if w["widget"]["name"].endswith("-history")]
    assert len(charts) == 4
    for chart in charts:
        spec = chart["spec"]["jsonSpec"]["spec"]
        assert "range_start_date" in spec and "SHARED_DOMAIN" not in spec and '"domain": [{"expr"' not in spec


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
    for table in space["data_sources"]["tables"]:
        names = [c["column_name"] for c in table.get("column_configs", [])]
        assert names == sorted(names), table["identifier"]


def test_genie_examples_name_the_catalog_and_no_parameters():
    space = json.loads(market_climate_genie.build())["resources"]["genie_spaces"]["market_climate_genie"]["serialized_space"]
    for example in space["instructions"]["example_question_sqls"]:
        sql = example["sql"][0]
        assert ":as_of_date" not in sql and ":sector_name" not in sql and ":company_name" not in sql and ":range_code" not in sql and ":history_range_code" not in sql and ":currency_code" not in sql and ":fund_code" not in sql and ":setup_period" not in sql
        assert "${var.catalog}.gold_analytics_gateway." in sql or "${var.catalog}.silver_domain_investments." in sql
        assert " FROM monitor_daily_signal" not in sql and " JOIN silver_domain_investments." not in sql


def test_inflation_dashboard_file_equals_its_builder():
    from common import inflation_dashboard

    committed = (ROOT / "src" / "dashboards" / "inflation_deflation.lvdash.json").read_text(encoding="utf-8")
    assert committed.replace("\r\n", "\n") == inflation_dashboard.build()


def test_currency_dashboard_file_equals_its_builder():
    from common import currency_dashboard

    committed = (ROOT / "src" / "dashboards" / "currency_monitor.lvdash.json").read_text(encoding="utf-8")
    assert committed.replace("\r\n", "\n") == currency_dashboard.build()


def test_strategy_dashboard_file_equals_its_builder():
    from common import strategy_dashboard

    committed = (ROOT / "src" / "dashboards" / "strategy_monitor.lvdash.json").read_text(encoding="utf-8")
    assert committed.replace(chr(13) + chr(10), chr(10)) == strategy_dashboard.build()


def test_strategy_dashboard_pages_datasets_and_parameters():
    from common import strategy_dashboard

    dashboard = json.loads(strategy_dashboard.build())
    assert [p["displayName"] for p in dashboard["pages"]] == ["Bear Market Fund", "Bear Fund Deep Dive", "Short Selling", "Efficient Stocks", "Company Deep Dive", "Filters"]
    datasets = {d["name"]: d for d in dashboard["datasets"]}
    assert all(d["queryLines"][0].strip() for d in datasets.values())
    assert {p["keyword"] for p in datasets["ds_fund_chart"]["parameters"]} == {"fund_code", "history_range_code"}
    assert {p["keyword"] for p in datasets["ds_bear_period_events"]["parameters"]} == {"setup_period"}
    assert {p["keyword"] for p in datasets["ds_short_candidates"]["parameters"]} == {"as_of_date"}
    assert {p["keyword"] for p in datasets["ds_efficient_closest"]["parameters"]} == {"as_of_date"}
    assert {p["keyword"] for p in datasets["ds_efficient_summary"]["parameters"]} == {"as_of_date"}
    widgets = {w["widget"]["name"] for page in dashboard["pages"] for w in page["layout"]}
    assert {"bear-week", "bear-checks", "bear-funds", "fund-chart", "short-candidates", "short-gate"} <= widgets
    chart = next(w["widget"] for page in dashboard["pages"] for w in page["layout"] if w["widget"]["name"] == "fund-chart")
    assert "range_start_date" in chart["spec"]["jsonSpec"]["spec"]


def test_strategy_queries_read_the_shared_states_and_use_the_rule_thresholds():
    from common.strategy_queries import DATASETS

    assert "is_setup_on" in DATASETS["ds_short_candidates"][1] and "is_setup_on" in DATASETS["ds_bear_week"][1]
    assert "-0.05" in DATASETS["ds_bear_week"][1] and "-0.025" in DATASETS["ds_bear_week"][1]
    assert ":as_of_date" in DATASETS["ds_bear_week"][1] and ":setup_period" in DATASETS["ds_bear_period_events"][1]


def test_the_efficient_stocks_screen_decides_on_tr60_and_volume_not_r60():
    from common.strategy_queries import DATASETS

    closest = DATASETS["ds_efficient_closest"][1]
    assert "efficiency_tr60_ratio >= 15" in closest and "volume_sixty_day_average_count > 200000" in closest
    assert "ORDER BY efficiency_tr60_ratio DESC" in closest
    assert "efficiency_r60_ratio >=" not in closest and "efficiency_r60_ratio >=" not in DATASETS["ds_efficient_summary"][1]
