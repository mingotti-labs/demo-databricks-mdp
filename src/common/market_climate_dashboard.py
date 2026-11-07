"""Builds the Market Climate dashboard JSON from the shared dataset queries (openspec market-climate-dashboard).

`build()` returns the file content of `src/dashboards/market_climate.lvdash.json`; `cicd/build_dashboards.py`
writes it and a test checks the committed file equals it.
"""

import json

from common.dashboard_widgets import (
    AXIS_WIDTH,
    GREEN,
    INK,
    NUMBER0,
    NUMBER2,
    NUMBER4,
    PALETTE,
    PERCENT,
    RED,
    TEXT_COLOR,
    YELLOW,
    Y_PADDING,
    dashboard_json,
    dataset_entries,
    date_parameter,
    filter_widget,
    range_time_x,
    string_parameter,
    table,
    text,
    vega,
    with_range_dates,
)
from common.company_page import company_page, company_parameters
from common.market_climate_queries import DATASETS

DATE_DATASETS = [
    "ds_freshness", "ds_lights", "ds_answers", "ds_index_day", "ds_top_up", "ds_top_down", "ds_excluded",
    "ds_members", "ds_checks", "ds_company_check", "ds_company_price", "ds_company_figures", "ds_sectors", "ds_sector_up", "ds_sector_down",
]
SECTOR_DATASETS = ["ds_sector_up", "ds_sector_down"]
HISTORY_DATASETS = ["ds_light_history", "ds_pe_history", "ds_fed_history", "ds_trend_history"]


def parameters(dataset: str) -> list[dict]:
    result = []
    if dataset in DATE_DATASETS:
        result.append(date_parameter())
    if dataset in SECTOR_DATASETS:
        result.append(string_parameter("sector_name", "Sector", "Information Technology"))
    result.extend(company_parameters(dataset))
    if dataset in HISTORY_DATASETS:
        result.append(string_parameter("history_range_code", "History range", "36M"))
    return result


def traffic_lights(name: str, x: int, y: int, w: int, h: int) -> dict:
    """Big coloured circle per climate (custom Vega-Lite), driven by ds_lights; the title carries the climate date."""
    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v6.json", "data": {"name": "databricks_query"},
        "width": "container", "height": "container", "config": {"autosize": {"type": "fit", "contains": "padding"}},
        "transform": [{"calculate": "datum.yes_count + '/3'", "as": "yes_label"},
                      {"calculate": "datum.lens_code == 'long_run' ? 'Long Run' : 'Modern'", "as": "lens_label"}],
        "title": {"text": {"expr": "'Market Climate as of ' + utcFormat(toDate(data('databricks_query')[0].climate_date), '%Y-%m-%d')"}, "anchor": "start", "fontSize": 16, "color": TEXT_COLOR},
        "encoding": {"x": {"field": "lens_label", "type": "nominal", "sort": ["Long Run", "Modern"],
                           "axis": {"title": None, "orient": "top", "labelFontSize": 18, "labelAngle": 0, "labelColor": TEXT_COLOR, "domain": False, "ticks": False}},
                     "tooltip": [{"field": "lens_name", "title": "Climate"}, {"field": "action_name", "title": "Action"}, {"field": "reason_text", "title": "Why"}]},
        "layer": [
            {"mark": {"type": "circle", "size": 14000},
             "encoding": {"y": {"value": 95}, "color": {"field": "light_code", "type": "nominal", "legend": None,
                          "scale": {"domain": ["red", "yellow", "green"], "range": [RED, YELLOW, GREEN]}}}},
            {"mark": {"type": "text", "fontSize": 22, "fontWeight": "bold", "color": INK},
             "encoding": {"y": {"value": 95}, "text": {"field": "yes_label"}}},
        ],
    }
    names = ["lens_name", "lens_code", "yes_count", "light_code", "action_name", "reason_text", "climate_date"]
    return {"widget": {"name": name,
                       "queries": [{"name": "main_query", "query": {"datasetName": "ds_lights", "fields": [{"name": n, "expression": f"`{n}`"} for n in names], "disaggregated": True}}],
                       "spec": {"version": 1, "widgetType": "custom-vega-viz", "jsonSpec": {"type": "vega-lite", "spec": json.dumps(spec)},
                                "encodings": {"fields": [{"fieldName": n} for n in names]}, "data": {"queryName": "main_query"},
                                "frame": {"showTitle": False}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}




def light_history(x: int, y: int, w: int, h: int) -> dict:
    """Both climates; the long-run line is drawn wide and pale under the thin modern line so equal answers stay visible."""
    time_x = range_time_x("signal_date")
    spec = {"encoding": {"x": time_x, "y": {"field": "yes_count", "type": "quantitative", "title": "Yes answers", "scale": {"domain": [0, 3], "padding": Y_PADDING}, "axis": {"tickMinStep": 1, "minExtent": AXIS_WIDTH}},
                         "color": {"field": "lens_name", "type": "nominal", "title": "Climate", "legend": {"orient": "top"}},
                         "tooltip": [{"field": "signal_date", "type": "temporal", "title": "Day"}, {"field": "lens_name", "title": "Climate"}, {"field": "yes_count", "title": "Yes answers"}]},
            "layer": [{"transform": [{"filter": "datum.lens_code == 'long_run'"}], "mark": {"type": "line", "strokeWidth": 9, "opacity": 0.35, "interpolate": "step-after"}},
                      {"transform": [{"filter": "datum.lens_code == 'modern'"}], "mark": {"type": "line", "strokeWidth": 2.5, "interpolate": "step-after"}}]}
    return vega("light-history", "Yes answers per day (0 green, 1 yellow, 2 or 3 red)", "ds_light_history",
                ["signal_date", "lens_name", "lens_code", "yes_count", "range_start_date", "range_end_date"], with_range_dates(spec), x, y, w, h,
                "Both climates are drawn; where the wide pale line shows around the thin one, they gave the same answer.")


def fed_history(x: int, y: int, w: int, h: int) -> dict:
    """Target rate line over a background: red within 6 months of a hike, green within 6 months of a cut."""
    time_x = range_time_x("signal_date")
    spec = {"layer": [
        {"transform": [{"window": [{"op": "lead", "field": "signal_date", "as": "next_date"}], "sort": [{"field": "signal_date"}]},
                       {"filter": "datum.fed_band_code == 'red' || datum.fed_band_code == 'green'"}],
         "mark": {"type": "rect", "opacity": 0.22},
         "encoding": {"x": time_x, "x2": {"field": "next_date"}, "y": {"value": 0}, "y2": {"value": {"expr": "height"}},
                      "color": {"field": "fed_band_code", "type": "nominal", "title": "Fed",
                                "scale": {"domain": ["red", "green"], "range": [RED, GREEN]},
                                "legend": {"orient": "top", "labelExpr": "datum.value == 'red' ? 'in the way (hike)' : 'out of the way (cut)'"}}}},
        {"mark": {"type": "line", "interpolate": "step-after", "strokeWidth": 2.5, "color": "#2B3A55"},
         "encoding": {"x": time_x, "y": {"field": "fed_target_rate", "type": "quantitative", "title": "Target rate (%)", "scale": {"zero": True, "nice": True, "padding": Y_PADDING}, "axis": {"format": ".2f", "tickCount": 6, "minExtent": AXIS_WIDTH}},
                      "tooltip": [{"field": "signal_date", "type": "temporal", "title": "Day"}, {"field": "fed_target_rate", "title": "Target rate (%)"}]}}]}
    return vega("fed-history", "Fed target rate (upper limit), percent", "ds_fed_history", ["signal_date", "fed_target_rate", "fed_band_code", "range_start_date", "range_end_date"], with_range_dates(spec), x, y, w, h,
                "Red background: within 6 months of a hike. Green background: within 6 months of a cut.")


def trend_history(x: int, y: int, w: int, h: int) -> dict:
    """S&P 500 and its 200-day average on the same time axis and left margin as the Fed chart."""
    time_x = range_time_x("signal_date")
    spec = {"transform": [{"fold": ["sp500_close", "sp500_average_200"], "as": ["series", "value"]},
                          {"calculate": "datum.series == 'sp500_close' ? 'S&P 500 close' : '200-day average'", "as": "series_label"}],
            "mark": {"type": "line", "strokeWidth": 2},
            "encoding": {"x": time_x,
                         "y": {"field": "value", "type": "quantitative", "title": "Index points", "scale": {"zero": False, "padding": Y_PADDING},
                               "axis": {"format": ",.0f", "minExtent": AXIS_WIDTH}},
                         "color": {"field": "series_label", "type": "nominal", "title": None, "legend": {"orient": "top"}},
                         "tooltip": [{"field": "signal_date", "type": "temporal", "title": "Day"}, {"field": "series_label", "title": "Line"},
                                     {"field": "value", "type": "quantitative", "format": ",.2f", "title": "Value"}]}}
    return vega("trend-history", "S&P 500 and its 200-day average", "ds_trend_history", ["signal_date", "sp500_close", "sp500_average_200", "range_start_date", "range_end_date"], with_range_dates(spec), x, y, w, h,
                "Same dates and left margin as the Fed chart, so the two can be read one above the other.")


def pe_history(x: int, y: int, w: int, h: int) -> dict:
    """Index P/E, both measures, with the three band lines drawn once each."""
    time_x = range_time_x("valuation_date")
    lines = [(16, "cheap line, long run", GREEN), (22, "expensive line, long run", YELLOW), (30, "expensive line, modern", RED)]
    spec = {"layer": [
        {"transform": [{"fold": ["pe_ten_year_adjusted", "pe_trailing"], "as": ["series", "value"]},
                       {"calculate": "datum.series == 'pe_trailing' ? 'Trailing 12 months' : '10-year inflation-adjusted (votes)'", "as": "series_label"}],
         "mark": {"type": "line", "strokeWidth": 2},
         "encoding": {"x": time_x, "y": {"field": "value", "type": "quantitative", "title": "Price/earnings ratio", "scale": {"zero": True, "padding": Y_PADDING}, "axis": {"format": ".0f", "minExtent": AXIS_WIDTH}},
                      "color": {"field": "series_label", "type": "nominal", "title": None, "legend": {"orient": "top"}},
                      "tooltip": [{"field": "valuation_date", "type": "temporal", "title": "Day"}, {"field": "series_label", "title": "Measure"},
                                  {"field": "value", "type": "quantitative", "format": ".2f", "title": "P/E"}]}}]
        + [{"transform": [{"window": [{"op": "row_number", "as": "row_rank"}]}, {"filter": "datum.row_rank == 1"}],
            "mark": {"type": "rule", "strokeDash": [6, 4], "color": color, "strokeWidth": 1.5},
            "encoding": {"y": {"datum": value, "type": "quantitative"}}} for value, _, color in lines]
        + [{"transform": [{"window": [{"op": "row_number", "as": "row_rank"}]}, {"filter": "datum.row_rank == 1"}],
            "mark": {"type": "text", "align": "left", "dx": 4, "dy": -6, "fontSize": 11, "color": TEXT_COLOR},
            "encoding": {"x": {"value": 0}, "y": {"datum": value, "type": "quantitative"}, "text": {"value": label}}} for value, label, _ in lines]}
    return vega("pe-history", "S&P 500 price/earnings ratio", "ds_pe_history", ["valuation_date", "pe_ten_year_adjusted", "pe_trailing", "range_start_date", "range_end_date"], with_range_dates(spec), x, y, w, h,
                "Price over earnings of the current members. Valuation answer: too expensive above 22 (long run) or 30 (modern).")


def sector_bars(x: int, y: int, w: int, h: int) -> dict:
    spec = {"mark": {"type": "bar"},
            "encoding": {"x": {"field": "sector_name", "type": "nominal", "sort": "-y", "title": None, "axis": {"labelAngle": -30}},
                         "y": {"field": "sector_pe", "type": "quantitative", "title": "Sector P/E", "scale": {"zero": True, "padding": Y_PADDING}},
                         "color": {"value": PALETTE[0]},
                         "tooltip": [{"field": "sector_name", "title": "Sector"}, {"field": "sector_pe", "type": "quantitative", "format": ".2f", "title": "Sector P/E"}]}}
    return vega("sector-pe", "Sector P/E", "ds_sectors", ["sector_name", "sector_pe"], spec, x, y, w, h)




def climate_page() -> dict:
    lights = [("lens_name", "Climate", None), ("yes_count", "Yes answers (of 3)", NUMBER0),
              ("light_code", "Light", None, "light"), ("action_name", "Action", None), ("reason_text", "Why", None)]
    answers = [("lens_name", "Climate", None), ("signal_name", "Question", None), ("answer_text", "Answer", None),
               ("band_code", "Band", None, "light"), ("measured_value", "Measured", NUMBER2),
               ("threshold_value", "Compared with", NUMBER2), ("reason_text", "Why", None)]
    dates = [("climate_date", "Climate as of", None), ("sp500_price_date", "Latest S&P 500 price", None),
             ("fed_rate_date", "Latest Fed target reading", None), ("cpi_date", "Latest CPI reading (monthly, carried forward)", None)]
    return {"name": "climate", "displayName": "Market Climate Monitor", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": [
        text("climate-title", ["# Market Climate Monitor\n", "\n", "Two climates read the same three questions. Yes is the unfavourable answer.\n", "\n", "- Is the market too expensive?\n", "- Is the Fed in the way?\n", "- Is the market going up?\n", "\n", "- Red (2 or 3 yes): sell\n", "- Yellow (1 yes): buy and hold\n", "- Green (0 yes): strong buy\n", "\n", "Change the date at the top and the history range above the charts. The other pages show the numbers behind the valuation answer."], 0, 0, 12, 5),
        traffic_lights("traffic-lights", 0, 5, 12, 6),
        filter_widget("filter-history-range", "History range (the four charts below)", "filter-single-select",
                      [("ds_history_range_options", "field", "history_range_code")] + [(d, "parameter", "history_range_code") for d in HISTORY_DATASETS], 0, 11, 6),
        light_history(0, 13, 12, 5),
        pe_history(0, 18, 12, 6),
        fed_history(0, 24, 12, 6),
        trend_history(0, 30, 12, 6),
        table("answers", "The three answers of each climate", "ds_answers", answers, 0, 36, 12, 7),
        table("lights", "Lights of the day", "ds_lights", lights, 0, 43, 12, 3),
        table("data-dates", "Data dates", "ds_freshness", dates, 0, 46, 12, 3,
              "The climate is shown as of the latest day on or before the chosen date; the other columns say how fresh each input is."),
    ]}


def deep_dive_page() -> dict:
    index_day = [("valuation_date", "Day", None), ("market_value_trillion", "Market value (US$ trillion)", NUMBER2),
                 ("earnings_adjusted_billion", "10-year adjusted earnings (US$ billion)", NUMBER2),
                 ("pe_ten_year_adjusted", "P/E 10-year adjusted", NUMBER2), ("pe_trailing", "P/E trailing", NUMBER2),
                 ("members_used_count", "Members used", NUMBER0), ("member_count", "Members", NUMBER0),
                 ("members_without_shares_count", "Without shares", NUMBER0), ("members_under_ten_years_count", "Under 10 years", NUMBER0)]
    checks = [("index_used_count", "Used (index row)", NUMBER0), ("member_used_count", "Used (member rows)", NUMBER0),
              ("market_value_difference_amount", "Market value difference (US$)", NUMBER2),
              ("earnings_difference_amount", "Earnings difference (US$)", NUMBER2),
              ("pe_index", "P/E index row", NUMBER4), ("pe_from_members", "P/E from member rows", NUMBER4)]
    members = [("company_name", "Company", None), ("sector_name", "Sector", None), ("market_value_share_ratio", "Share of market value", PERCENT),
               ("member_pe", "P/E 10-year adjusted", NUMBER2), ("member_pe_trailing", "P/E trailing", NUMBER2), ("pe_without_member", "Index P/E without it", NUMBER2),
               ("pe_effect", "Effect on index P/E", NUMBER4)]
    everyone = members + [("is_used", "Used", None), ("exclusion_reason_code", "Left out because", None),
                          ("price_close", "Close (US$)", NUMBER2), ("share_count", "Shares", NUMBER0),
                          ("market_value_billion", "Market value (US$ billion)", NUMBER2)]
    excluded = [("company_name", "Company", None), ("sector_name", "Sector", None), ("exclusion_reason_code", "Left out because", None),
                ("price_date", "Price date", None)]
    return {"name": "deep-dive", "displayName": "Climate Deep Dive", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": [
        text("dive-title", ["# Climate Deep Dive\n", "\n", "Checks the valuation answer. The P/E is the sum of the members' market values over the sum of their "
             "10-year inflation-adjusted earnings. Effect on index P/E = index P/E minus the P/E without that member: positive pushes the ratio up, negative down. "
             "Effects are one at a time and do not add up."], 0, 0, 12, 3),
        table("index-day", "The index of the day", "ds_index_day", index_day, 0, 3, 12, 3),
        table("checks", "Checks: member rows against the index row (differences should be 0)", "ds_checks", checks, 0, 6, 12, 3),
        text("up-down-title", ["## Who moves the ratio\n"], 0, 9, 12, 1),
        table("top-up", "Top 10 pushing the P/E up", "ds_top_up", members, 0, 10, 6, 8),
        table("top-down", "Top 10 pushing the P/E down", "ds_top_down", members, 6, 10, 6, 8),
        text("left-out-title", ["## Members left out of the day\n"], 0, 18, 12, 1),
        table("excluded", "Left out", "ds_excluded", excluded, 0, 19, 12, 6),
        text("all-title", ["## All members\n"], 0, 25, 12, 1),
        filter_widget("filter-sector-members", "Sector", "filter-multi-select", [("ds_members", "field", "sector_name")], 0, 26, 6),
        filter_widget("filter-used-members", "Used", "filter-multi-select", [("ds_members", "field", "is_used")], 6, 26, 6),
        table("all-members", "Every current member, largest first", "ds_members", everyone, 0, 28, 12, 10),
    ]}


def sector_page() -> dict:
    sectors = [("sector_name", "Sector", None), ("member_count", "Members used", NUMBER0), ("market_value_trillion", "Market value (US$ trillion)", NUMBER2),
               ("market_value_share_ratio", "Share of market value", PERCENT), ("sector_pe", "Sector P/E", NUMBER2),
               ("pe_without_sector", "Index P/E without the sector", NUMBER2), ("pe_index", "Index P/E", NUMBER2)]
    members = [("company_name", "Company", None), ("market_value_share_ratio", "Share of index market value", PERCENT),
               ("member_pe", "P/E 10-year adjusted", NUMBER2), ("member_pe_trailing", "P/E trailing", NUMBER2), ("pe_without_member", "Index P/E without it", NUMBER2),
               ("pe_effect", "Effect on index P/E", NUMBER4)]
    return {"name": "sector-deep-dive", "displayName": "Sector Deep Dive", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": [
        text("sector-title", ["# Sector Deep Dive\n", "\n", "Sector P/E = the sector's market value over its 10-year inflation-adjusted earnings. "
             "Index P/E without the sector shows how much the sector lifts or lowers the index ratio. Sectors are today's sectors (GICS), "
             "applied to every day."], 0, 0, 12, 3),
        table("sectors", "Every sector on the day", "ds_sectors", sectors, 0, 3, 12, 7),
        sector_bars(0, 10, 12, 5),
        filter_widget("filter-sector", "Sector", "filter-single-select",
                      [("ds_sector_names", "field", "sector_name"), ("ds_sector_up", "parameter", "sector_name"),
                       ("ds_sector_down", "parameter", "sector_name")], 0, 15, 6),
        table("sector-up", "Chosen sector: top 10 pushing the index P/E up", "ds_sector_up", members, 0, 17, 6, 8),
        table("sector-down", "Chosen sector: top 10 pushing the index P/E down", "ds_sector_down", members, 6, 17, 6, 8),
    ]}


def filters_page() -> dict:
    return {"name": "filters", "displayName": "Filters", "pageType": "PAGE_TYPE_GLOBAL_FILTERS", "layoutVersion": "GRID_V1", "layout": [
        filter_widget("filter-as-of", "As of date (latest day on or before it)", "filter-date-picker",
                      [(d, "parameter", "as_of_date") for d in DATE_DATASETS], 0, 0, 4)]}


def build() -> str:
    pages = [climate_page(), deep_dive_page(), company_page(), sector_page(), filters_page()]
    return dashboard_json(dataset_entries(DATASETS, parameters), pages)
