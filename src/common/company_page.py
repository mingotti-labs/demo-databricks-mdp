"""The Company Deep Dive page shared by the dashboards (spike shared-company-deep-dive).

One page, built once: the price with its Bollinger bands, the last close and the 52-week range, and the steps that turn the
company's filing and price into the P/E of the market climate. A dashboard adds `company_page()` to its pages, the datasets of
`company_datasets()` to its datasets, `company_parameters(dataset)` to their parameters and the date-bound ones
(`DATE_BOUND`) to the datasets its as-of date filter drives. Drill-through between dashboards is not used: Databricks drills
through only between pages that share a dataset, so the company is picked in the page's own dropdown.
"""

from common.dashboard_widgets import (
    NUMBER0,
    PALETTE,
    Y_PADDING,
    counter,
    filter_widget,
    string_parameter,
    table,
    text,
    vega,
)
from common.market_climate_queries import DATASETS

DATASET_NAMES = ["ds_company_names", "ds_company_check", "ds_company_price", "ds_company_figures", "ds_range_options"]
DATE_BOUND = ["ds_company_check", "ds_company_price", "ds_company_figures"]
COMPANY_PARAMETER_DATASETS = ["ds_company_check", "ds_company_price", "ds_company_figures"]
RANGE_PARAMETER_DATASETS = ["ds_company_price"]


def company_datasets() -> dict[str, tuple[str, str]]:
    """The dataset queries of the page: {name: (title, query)}."""
    return {name: DATASETS[name] for name in DATASET_NAMES}


def company_parameters(dataset: str) -> list[dict]:
    """The company and price range parameters of the page's datasets (the date parameter belongs to the dashboard)."""
    result = []
    if dataset in COMPANY_PARAMETER_DATASETS:
        result.append(string_parameter("company_name", "Company", "EQT Corporation"))
    if dataset in RANGE_PARAMETER_DATASETS:
        result.append(string_parameter("range_code", "Range", "6M"))
    return result


def company_price(x: int, y: int, w: int, h: int) -> dict:
    """Close line with the Bollinger bands."""
    spec = {"transform": [{"fold": ["price_close", "band_upper", "band_middle", "band_lower"], "as": ["series", "value"]},
                          {"calculate": "{'price_close': 'Close', 'band_upper': 'Upper band', 'band_middle': '20-day average', 'band_lower': 'Lower band'}[datum.series]", "as": "series_label"}],
            "mark": {"type": "line", "strokeWidth": 2},
            "encoding": {"x": {"field": "price_date", "type": "temporal", "title": None},
                         "y": {"field": "value", "type": "quantitative", "title": "US$", "scale": {"zero": False, "padding": Y_PADDING}},
                         "color": {"field": "series_label", "type": "nominal", "title": None, "legend": {"orient": "top"},
                                   "scale": {"domain": ["Close", "Upper band", "20-day average", "Lower band"], "range": [PALETTE[0], PALETTE[1], PALETTE[2], PALETTE[1]]}},
                         "strokeDash": {"field": "series_label", "type": "nominal", "legend": None,
                                        "scale": {"domain": ["Close", "Upper band", "20-day average", "Lower band"], "range": [[1, 0], [5, 3], [1, 0], [5, 3]]}},
                         "tooltip": [{"field": "price_date", "type": "temporal", "title": "Day"}, {"field": "series_label", "title": "Line"},
                                     {"field": "value", "type": "quantitative", "format": ",.2f", "title": "US$"}]}}
    return vega("company-price", "Close with Bollinger bands", "ds_company_price", ["price_date", "price_close", "band_upper", "band_middle", "band_lower"], spec, x, y, w, h,
                "Bands: 20-day average of the close, plus and minus 2 standard deviations.")


def company_page() -> dict:
    steps = [("step_number", "Step", NUMBER0), ("step_name", "What", None), ("value_text", "Value", None), ("how_text", "How", None)]
    money = {"type": "number", "decimalPlaces": {"type": "exact", "places": 2}}
    percent = {"type": "number-percent", "decimalPlaces": {"type": "exact", "places": 2}}
    return {"name": "company-deep-dive", "displayName": "Company Deep Dive", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": [
        text("company-title", ["# Company Deep Dive\n", "\n", "Pick a company: its price first, then the steps that turn its filing and price into the P/E the climate uses.\n", "\n", "- Step 5 is the trailing P/E finance sites show\n", "- Step 9 is the one the climate uses; they differ when earnings were low in earlier years\n", "- Bollinger bands: 20-day average of the close, plus and minus 2 standard deviations"], 0, 0, 12, 4),
        filter_widget("filter-company", "Company", "filter-single-select",
                      [("ds_company_names", "field", "company_name"), ("ds_company_check", "parameter", "company_name"),
                       ("ds_company_price", "parameter", "company_name"), ("ds_company_figures", "parameter", "company_name")], 0, 4, 6),
        filter_widget("filter-range", "Range", "filter-single-select",
                      [("ds_range_options", "field", "range_code"), ("ds_company_price", "parameter", "range_code")], 6, 4, 6),
        counter("last-close", "Last close (US$)", "ds_company_figures", "last_close", money, 0, 6, 3, 3),
        counter("day-change", "Change on the day", "ds_company_figures", "day_change_ratio", percent, 3, 6, 3, 3),
        counter("high-52", "52-week high (US$)", "ds_company_figures", "high_52_weeks", money, 6, 6, 3, 3),
        counter("low-52", "52-week low (US$)", "ds_company_figures", "low_52_weeks", money, 9, 6, 3, 3),
        company_price(0, 9, 12, 8),
        table("company-steps", "From the numbers to the P/E", "ds_company_check", steps, 0, 17, 12, 10),
    ]}
