import json

from common import currency_dashboard, inflation_dashboard, market_climate_dashboard, strategy_dashboard
from common.company_page import DATASET_NAMES, DATE_BOUND

BUILDERS = {
    "market climate": market_climate_dashboard,
    "inflation": inflation_dashboard,
    "currency": currency_dashboard,
    "strategy": strategy_dashboard,
}


def page(dashboard: dict) -> dict:
    return next(p for p in dashboard["pages"] if p["name"] == "company-deep-dive")


def test_every_dashboard_has_the_same_company_page():
    pages = {name: page(json.loads(module.build())) for name, module in BUILDERS.items()}
    first = pages["market climate"]
    assert all(other == first for other in pages.values())
    assert first["displayName"] == "Company Deep Dive"


def test_every_dashboard_carries_the_company_datasets_and_their_parameters():
    for name, module in BUILDERS.items():
        datasets = {d["name"]: d for d in json.loads(module.build())["datasets"]}
        assert set(DATASET_NAMES) <= set(datasets), name
        for dataset in DATE_BOUND:
            keywords = {p["keyword"] for p in datasets[dataset]["parameters"]}
            assert {"as_of_date", "company_name"} <= keywords, (name, dataset)
        assert "range_code" in {p["keyword"] for p in datasets["ds_company_price"]["parameters"]}


def test_the_date_filter_of_every_dashboard_drives_the_company_datasets():
    for name, module in BUILDERS.items():
        filters = next(p for p in json.loads(module.build())["pages"] if p["name"] == "filters")
        bound = {q["query"]["datasetName"] for w in filters["layout"] for q in w["widget"]["queries"]}
        assert set(DATE_BOUND) <= bound, name
