"""Builds the Inflation Deflation dashboard JSON from its dataset queries (openspec inflation-deflation-monitor).

`build()` returns the file content of `src/dashboards/inflation_deflation.lvdash.json`; `cicd/build_dashboards.py`
writes it and a test checks the committed file equals it. Same date axis, colours and theme as Market Climate.
"""

import json

from common.dashboard_widgets import (
    AXIS_WIDTH,
    GREEN,
    INK,
    NUMBER2,
    PERCENT,
    RED,
    SHARED_DOMAIN,
    TEXT_COLOR,
    TIME_AXIS,
    YELLOW,
    Y_PADDING,
    dashboard_json,
    dataset_entries,
    date_parameter,
    filter_widget,
    table,
    text,
    vega,
)
from common.inflation_queries import DATASETS

BLUE = "#4E79A7"
DATE_DATASETS = ["ds_inflation_freshness", "ds_rating", "ds_stars", "ds_commodities"]
BAND_SCALE = {"domain": ["red", "yellow", "green", "blue"], "range": [RED, YELLOW, GREEN, BLUE]}
SCHEMA = "https://vega.github.io/schema/vega-lite/v6.json"
BASE = {"$schema": SCHEMA, "data": {"name": "databricks_query"}, "width": "container", "height": "container",
        "config": {"autosize": {"type": "fit", "contains": "padding"}}}


def parameters(dataset: str) -> list[dict]:
    return [date_parameter()] if dataset in DATE_DATASETS else []


def custom(name: str, dataset: str, fields: list[str], spec: dict, x: int, y: int, w: int, h: int, title: str | None = None) -> dict:
    """A Vega-Lite widget without the standard title bar (the title is drawn inside when `spec` has one)."""
    return {"widget": {"name": name,
                       "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": [{"name": n, "expression": f"`{n}`"} for n in fields], "disaggregated": True}}],
                       "spec": {"version": 1, "widgetType": "custom-vega-viz", "jsonSpec": {"type": "vega-lite", "spec": json.dumps({**BASE, **spec})},
                                "encodings": {"fields": [{"fieldName": n} for n in fields]}, "data": {"queryName": "main_query"},
                                "frame": {"showTitle": bool(title), **({"title": title} if title else {})}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def rating_tile(x: int, y: int, w: int, h: int) -> dict:
    """The rating of the day: one circle in the colour of its band, the stars on, the label and the date."""
    spec = {
        "title": {"text": {"expr": "'Inflation rating as of ' + utcFormat(toDate(data('databricks_query')[0].rating_date), '%Y-%m-%d')"},
                  "anchor": "start", "fontSize": 16, "color": TEXT_COLOR},
        "transform": [{"calculate": "datum.stars_on + '/4'", "as": "stars_label"}],
        "encoding": {"x": {"field": "label", "type": "nominal", "axis": {"title": None, "orient": "bottom", "labelFontSize": 17, "labelAngle": 0, "labelColor": TEXT_COLOR, "domain": False, "ticks": False}},
                     "tooltip": [{"field": "label", "title": "Rating"}, {"field": "reason_text", "title": "Why"}]},
        "layer": [
            {"mark": {"type": "circle", "size": 14000},
             "encoding": {"y": {"value": 90}, "color": {"field": "rating_band", "type": "nominal", "legend": None, "scale": BAND_SCALE}}},
            {"mark": {"type": "text", "fontSize": 22, "fontWeight": "bold", "color": INK},
             "encoding": {"y": {"value": 90}, "text": {"field": "stars_label"}}},
        ],
    }
    return custom("rating-tile", "ds_rating", ["rating_date", "stars_on", "label", "rating_band", "reason_text"], spec, x, y, w, h)


def stars_tile(x: int, y: int, w: int, h: int) -> dict:
    """The four stars of the day: red when on (points to inflation), green when off."""
    spec = {
        "title": {"text": "The four vehicles (red: pointing to inflation)", "anchor": "start", "fontSize": 16, "color": TEXT_COLOR},
        "encoding": {"x": {"field": "signal_name", "type": "nominal", "sort": {"field": "star_order"},
                           "axis": {"title": None, "orient": "bottom", "labelFontSize": 15, "labelAngle": 0, "labelColor": TEXT_COLOR, "domain": False, "ticks": False}},
                     "tooltip": [{"field": "signal_name", "title": "Vehicle"}, {"field": "reason_text", "title": "Why"}]},
        "layer": [
            {"mark": {"type": "circle", "size": 9000},
             "encoding": {"y": {"value": 90}, "color": {"field": "star_band", "type": "nominal", "legend": None, "scale": BAND_SCALE}}},
            {"mark": {"type": "text", "fontSize": 18, "fontWeight": "bold", "color": INK},
             "encoding": {"y": {"value": 90}, "text": {"field": "star_state"}}},
        ],
    }
    return custom("stars-tile", "ds_stars", ["signal_name", "star_order", "star_state", "star_band", "reason_text"], spec, x, y, w, h)


def time_lines(name: str, title: str, dataset: str, x_field: str, series: list[tuple[str, str]], y_title: str, x: int, y: int, w: int, h: int,
               y_format: str = ",.2f", zero: bool = False, step: bool = False, description: str | None = None) -> dict:
    """Lines over time on the shared date axis and left margin: `series` is (field, label), folded into one colour field."""
    time_x = {"field": x_field, "type": "temporal", "title": None, "scale": {"domain": SHARED_DOMAIN}, "axis": TIME_AXIS}
    labels = dict(series)
    spec = {"transform": [{"fold": [f for f, _ in series], "as": ["series", "value"]},
                          {"calculate": json.dumps(labels) + "[datum.series]", "as": "series_label"}],
            "mark": {"type": "line", "strokeWidth": 2, **({"interpolate": "step-after"} if step else {})},
            "encoding": {"x": time_x,
                         "y": {"field": "value", "type": "quantitative", "title": y_title, "scale": {"zero": zero, "padding": Y_PADDING},
                               "axis": {"format": y_format, "minExtent": AXIS_WIDTH}},
                         "color": {"field": "series_label", "type": "nominal", "title": None, "legend": {"orient": "top"}},
                         "tooltip": [{"field": x_field, "type": "temporal", "title": "Day"}, {"field": "series_label", "title": "Line"},
                                     {"field": "value", "type": "quantitative", "format": y_format, "title": y_title}]}}
    return vega(name, title, dataset, [x_field] + [f for f, _ in series], {k: v for k, v in spec.items()}, x, y, w, h, description)


def rating_history(x: int, y: int, w: int, h: int) -> dict:
    time_x = {"field": "signal_date", "type": "temporal", "title": None, "scale": {"domain": SHARED_DOMAIN}, "axis": TIME_AXIS}
    spec = {"mark": {"type": "line", "strokeWidth": 2.5, "interpolate": "step-after"},
            "encoding": {"x": time_x,
                         "y": {"field": "rating", "type": "quantitative", "title": "Rating (-1 to 4)", "scale": {"domain": [-1, 4], "padding": Y_PADDING},
                               "axis": {"tickMinStep": 1, "minExtent": AXIS_WIDTH}},
                         "tooltip": [{"field": "signal_date", "type": "temporal", "title": "Day"}, {"field": "label", "title": "Rating"}, {"field": "stars_on", "title": "Stars on"}]}}
    return vega("rating-history", "Rating per day (4 increasing inflation, 0 decreasing, -1 deflation)", "ds_rating_history", ["signal_date", "rating", "label", "stars_on"], spec, x, y, w, h)


def distance_bars(x: int, y: int, w: int, h: int) -> dict:
    spec = {"mark": {"type": "bar"},
            "encoding": {"y": {"field": "benchmark_name", "type": "nominal", "sort": None, "title": None, "axis": {"labelLimit": 220}},
                         "x": {"field": "distance_ratio", "type": "quantitative", "title": "Distance from the 200-day average", "axis": {"format": ".0%"}, "scale": {"padding": Y_PADDING}},
                         "color": {"condition": {"test": "datum.distance_ratio > 0", "value": RED}, "value": GREEN},
                         "tooltip": [{"field": "benchmark_name", "title": "Benchmark"}, {"field": "distance_ratio", "type": "quantitative", "format": ".1%", "title": "Distance"}]}}
    return vega("distance-bars", "Distance from the 200-day average, today (red above: rising prices)", "ds_commodities", ["benchmark_name", "distance_ratio"], spec, x, y, w, h)


def commodity_history(x: int, y: int, w: int, h: int) -> dict:
    time_x = {"field": "price_date", "type": "temporal", "title": None, "scale": {"domain": SHARED_DOMAIN}, "axis": TIME_AXIS}
    spec = {"mark": {"type": "line", "strokeWidth": 1.8},
            "encoding": {"x": time_x,
                         "y": {"field": "distance_ratio", "type": "quantitative", "title": "Distance from the 200-day average",
                               "scale": {"zero": False, "padding": Y_PADDING}, "axis": {"format": ".0%", "minExtent": AXIS_WIDTH}},
                         "color": {"field": "benchmark_name", "type": "nominal", "title": None, "legend": {"orient": "top", "columns": 4}},
                         "tooltip": [{"field": "price_date", "type": "temporal", "title": "Day"}, {"field": "benchmark_name", "title": "Benchmark"},
                                     {"field": "distance_ratio", "type": "quantitative", "format": ".1%", "title": "Distance"}]}}
    return vega("commodity-history", "Each benchmark against its 200-day average", "ds_commodities_history", ["price_date", "benchmark_name", "distance_ratio"], spec, x, y, w, h)


def game_plan_page() -> dict:
    stars = [("signal_name", "Vehicle", None), ("star_state", "Star", None), ("star_band", "Band", None, "light"), ("measured_value", "Measured", NUMBER2),
             ("threshold_value", "Compared with", NUMBER2), ("reason_text", "Why", None)]
    dates = [("rating_date", "Rating as of", None), ("crb_price_date", "Latest CRB price", None), ("gold_price_date", "Latest gold price", None),
             ("rate_date", "Latest federal funds reading", None), ("cpi_reading_date", "Latest CPI reading (monthly, counted from the first day of its month)", None)]
    return {"name": "game-plan", "displayName": "Game plan", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": [
        text("plan-title", ["# Inflation-Deflation Monitor\n", "\n", "Four vehicles each switch on a star when they point to inflation. The rating is the stars on.\n", "\n",
                            "- Commodity prices: the CRB index 200-day average is rising\n", "- Consumer prices: the 200-day average of US consumer prices is rising\n",
                            "- Gold prices: gold is above its 200-day average\n", "- Interest rates: the short-term rate (federal funds effective) is above its 200-day average\n", "\n",
                            "4 stars Increasing Inflation, 3 Inflation Danger, 2 Some Inflation Risk, 1 Mild or Decreasing Inflation, 0 Decreasing Inflation. "
                            "Minus one is Deflation: no star on and consumer prices below their level of a year ago.\n", "\n",
                            "Change the date at the top. Consumer prices count from the first day of their month, before they are published."], 0, 0, 12, 7),
        rating_tile(0, 7, 4, 6),
        stars_tile(4, 7, 8, 6),
        rating_history(0, 13, 12, 5),
        time_lines("crb-chart", "CRB commodity index and its 200-day average", "ds_crb_history", "price_date",
                   [("price_close", "CRB close"), ("average_200", "200-day average")], "Index points", 0, 18, 12, 6, ",.0f"),
        time_lines("cpi-chart", "US consumer price index and its 200-day average", "ds_cpi_history", "indicator_date",
                   [("rate_value", "Consumer price index"), ("average_200", "200-day average")], "Index points", 0, 24, 12, 6, ",.0f"),
        time_lines("gold-chart", "Gold futures and their 200-day average", "ds_gold_history", "price_date",
                   [("price_close", "Gold close"), ("average_200", "200-day average")], "US$", 0, 30, 12, 6, ",.0f"),
        time_lines("rate-chart", "Federal funds effective rate and its 200-day average", "ds_rate_history", "indicator_date",
                   [("rate_value", "Effective rate"), ("average_200", "200-day average")], "Percent", 0, 36, 12, 6, ".2f", zero=True),
        time_lines("real-rate-chart", "Real federal funds rate (effective rate minus consumer prices over 12 months)", "ds_real_rate_history", "indicator_date",
                   [("rate_value", "Real rate"), ("average_200", "200-day average")], "Percent", 0, 42, 12, 6, ".2f",
                   description="Shown for context; it does not vote. Negative means savers lose to inflation."),
        time_lines("cpi-change-chart", "US consumer price changes", "ds_cpi_changes", "indicator_date",
                   [("cpi_change", "Change")], "Percent", 0, 48, 12, 6, ".2f", step=True,
                   description="Over 12 months, and against the previous monthly reading, carried until the next one."),
        table("stars-table", "The four answers", "ds_stars", stars, 0, 54, 12, 6),
        table("plan-dates", "Data dates", "ds_inflation_freshness", dates, 0, 60, 12, 3,
              "The rating is shown as of the latest day on or before the chosen date; the other columns say how fresh each input is."),
    ]}


def commodities_page() -> dict:
    columns = [("benchmark_name", "Benchmark", None), ("price_close", "Close", NUMBER2), ("average_200", "200-day average", NUMBER2),
               ("distance_ratio", "Distance from the average", PERCENT), ("position_text", "Close is", None),
               ("slope_ratio", "Average moved over 20 days", PERCENT), ("direction_text", "Average is", None), ("price_date", "Price date", None)]
    return {"name": "commodities", "displayName": "Commodities", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": [
        text("commodities-title", ["# Commodities\n", "\n", "The eight commodity benchmarks against their 200-day averages, for context. "
                                   "Only the CRB index votes for the commodity star, and gold futures for the gold star.\n"], 0, 0, 12, 3),
        distance_bars(0, 3, 12, 6),
        table("commodities-table", "Benchmarks of the day", "ds_commodities", columns, 0, 9, 12, 7),
        commodity_history(0, 16, 12, 7),
    ]}


def filters_page() -> dict:
    return {"name": "filters", "displayName": "Filters", "pageType": "PAGE_TYPE_GLOBAL_FILTERS", "layoutVersion": "GRID_V1", "layout": [
        filter_widget("filter-as-of", "As of date (latest day on or before it)", "filter-date-picker",
                      [(d, "parameter", "as_of_date") for d in DATE_DATASETS], 0, 0, 4)]}


def build() -> str:
    return dashboard_json(dataset_entries(DATASETS, parameters), [game_plan_page(), commodities_page(), filters_page()])
