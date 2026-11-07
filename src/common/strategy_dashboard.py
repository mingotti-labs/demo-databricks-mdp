"""Builds the Strategy Monitor dashboard JSON from its dataset queries (openspec strategy-monitor-dashboard).

`build()` returns the file content of `src/dashboards/strategy_monitor.lvdash.json`; `cicd/build_dashboards.py` writes it
and a test checks the committed file equals it. Same colours and theme as the other dashboards; the deep dive chart takes
its history range from the same filter as the Market Climate page.
"""

from common.dashboard_widgets import (
    AXIS_WIDTH,
    BLUE,
    GREEN,
    NUMBER0,
    NUMBER2,
    PERCENT,
    RED,
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
from common.market_climate_queries import DATASETS as CLIMATE_DATASETS
from common.strategy_queries import DATASETS as STRATEGY_DATASETS

DATASETS = {**STRATEGY_DATASETS, "ds_history_range_options": CLIMATE_DATASETS["ds_history_range_options"]}
DATE_DATASETS = ["ds_strategy_freshness", "ds_bear_week", "ds_bear_checks", "ds_bear_funds", "ds_short_gate",
                 "ds_short_candidates", "ds_short_events"]
CHART_DATASETS = ["ds_fund_chart"]
GREY = "#8A8F98"


def parameters(dataset: str) -> list[dict]:
    result = [date_parameter()] if dataset in DATE_DATASETS else []
    if dataset == "ds_bear_period_events":
        result.append(string_parameter("setup_period", "Setup period", "all"))
    if dataset in CHART_DATASETS:
        result.append(string_parameter("fund_code", "Bear fund", "SQQQ"))
        result.append(string_parameter("history_range_code", "History range", "36M"))
    return result


def bear_page() -> dict:
    week = [("week_end_date", "Week ending", None), ("setup_text", "Setup", None), ("setup_light", "Light", None, "light"),
            ("week_change_ratio", "S&P 500 week change", PERCENT), ("entry_band_code", "Entry band", None), ("action_text", "What to do", None)]
    checks = [("step_group", "Step", None), ("check_name", "Check", None), ("answer_text", "Answer", None), ("value_text", "Value", None)]
    funds = [("fund_code", "Fund", None), ("fund_name", "Name", None), ("fund_description", "What it does", None),
             ("last_close", "Last close (US$)", NUMBER2), ("week_change_ratio", "Change over 5 trading days", PERCENT), ("last_date", "Price of", None)]
    events = [("event_date", "Date", None), ("event_name", "Event", None), ("setup_start_date", "Setup period starts", None),
              ("entry_number", "Entry no.", NUMBER0), ("entry_band_code", "Entry band", None), ("week_change_ratio", "Week change", PERCENT),
              ("reason_text", "Why", None)]
    dates = [("bear_week_date", "Week shown (strategy 001)", None), ("climate_date", "Latest market climate", None),
             ("sp500_price_date", "Latest S&P 500 price", None), ("latest_event_date", "Latest strategy event", None)]
    return {"name": "bear-market-fund", "displayName": "Bear Market Fund", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": [
        text("bear-title", ["# Strategy 001: Bear Market Mutual Fund\n", "\n", "Buy a bear fund when the market climate is red and the S&P 500 keeps falling.\n", "\n",
                            "- Setup: a market climate light is red and the S&P 500 closed the week below its close five weeks earlier\n",
                            "- Entry (Friday to Friday change): 5% down or more, invest half of equity; 2.5% to 5% down, a quarter; less than 2.5% down, watch Monday to Wednesday for a 2.5% drop\n",
                            "- Exit: up 3% on the week sell 10% of equity per 3%; a Friday close above five weeks earlier or a VIX above 50 sell everything\n",
                            "- Invest at most 50% of equity, in 25% steps\n", "\n",
                            "Change the date at the top: the week shown is the latest complete week on or before it."], 0, 0, 12, 7),
        table("bear-week", "Setup and entry of the week", "ds_bear_week", week, 0, 7, 12, 4),
        table("bear-checks", "The checks behind it", "ds_bear_checks", checks, 0, 11, 12, 9),
        table("bear-funds", "Bear funds", "ds_bear_funds", funds, 0, 20, 12, 7,
              "Pick one on the Bear Fund Deep Dive page. A 3x fund moves about three times the index each day."),
        filter_widget("filter-setup-period", "Past setup period", "filter-single-select",
                      [("ds_bear_periods", "field", "period_code"), ("ds_bear_period_events", "parameter", "setup_period")], 0, 27, 6),
        table("bear-period-events", "Events of the chosen setup period", "ds_bear_period_events", events, 0, 29, 12, 9),
        table("bear-dates", "Data dates", "ds_strategy_freshness", dates, 0, 38, 12, 3),
    ]}


def fund_chart(x: int, y: int, w: int, h: int) -> dict:
    """A bear fund and the S&P 500 on one time axis: setup periods shaded, entries marked."""
    time_x = range_time_x("price_date")
    fund_y = {"field": "fund_close", "type": "quantitative", "title": "Bear fund close (US$)",
              "scale": {"zero": False, "padding": Y_PADDING}, "axis": {"format": ",.2f", "minExtent": AXIS_WIDTH}}
    in_setup = "datum.is_in_setup == true || datum.is_in_setup == 'true'"
    spec = {
        "resolve": {"scale": {"y": "independent"}},
        "layer": [
            {"transform": [{"window": [{"op": "lead", "field": "price_date", "as": "next_date"}], "sort": [{"field": "price_date"}]},
                           {"filter": in_setup}],
             "mark": {"type": "rect", "opacity": 0.16, "color": RED},
             "encoding": {"x": time_x, "x2": {"field": "next_date"}, "y": {"value": 0}, "y2": {"value": {"expr": "height"}}}},
            {"mark": {"type": "line", "strokeWidth": 2.2, "color": BLUE},
             "encoding": {"x": time_x, "y": fund_y,
                          "tooltip": [{"field": "price_date", "type": "temporal", "title": "Day"},
                                      {"field": "fund_close", "type": "quantitative", "format": ",.2f", "title": "Fund close"}]}},
            {"mark": {"type": "line", "strokeWidth": 1.8, "color": GREY, "strokeDash": [4, 3]},
             "encoding": {"x": time_x,
                          "y": {"field": "sp500_close", "type": "quantitative", "title": "S&P 500 (index points)",
                                "scale": {"zero": False, "padding": Y_PADDING}, "axis": {"orient": "right", "format": ",.0f"}},
                          "tooltip": [{"field": "price_date", "type": "temporal", "title": "Day"},
                                      {"field": "sp500_close", "type": "quantitative", "format": ",.0f", "title": "S&P 500"}]}},
            {"mark": {"type": "point", "filled": True, "size": 130, "shape": "triangle-up", "color": GREEN},
             "encoding": {"x": time_x, "y": fund_y,
                          "opacity": {"condition": {"test": "datum.entry_band_code != null", "value": 1}, "value": 0},
                          "tooltip": [{"field": "price_date", "type": "temporal", "title": "Entry on"},
                                      {"field": "entry_band_code", "title": "Entry band"}]}},
        ],
    }
    return vega("fund-chart", "Bear fund and S&P 500: setup periods shaded, entries marked", "ds_fund_chart",
                ["price_date", "fund_close", "sp500_close", "is_in_setup", "entry_band_code", "range_start_date", "range_end_date"],
                with_range_dates(spec), x, y, w, h,
                "Red background: a strategy 001 setup period. Green triangle: an entry. The S&P 500 is on the right axis.")


def fund_page() -> dict:
    return {"name": "bear-fund-deep-dive", "displayName": "Bear Fund Deep Dive", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": [
        text("fund-title", ["# Bear Fund Deep Dive\n", "\n", "Pick a bear fund and a history range: the fund against the S&P 500, with the strategy 001 setup periods shaded and "
                            "the entries marked. SQQQ and PSQ follow the Nasdaq-100; SH, SDS and SPXU the S&P 500.\n"], 0, 0, 12, 3),
        filter_widget("filter-fund", "Bear fund", "filter-single-select",
                      [("ds_fund_options", "field", "fund_code"), ("ds_fund_chart", "parameter", "fund_code")], 0, 3, 6),
        filter_widget("filter-fund-range", "History range", "filter-single-select",
                      [("ds_history_range_options", "field", "history_range_code"), ("ds_fund_chart", "parameter", "history_range_code")], 6, 3, 6),
        fund_chart(0, 5, 12, 9),
    ]}


def short_page() -> dict:
    gate = [("climate_date", "Market climate of", None), ("gate_text", "Gate", None), ("gate_light", "Light", None, "light"), ("lights_text", "Lights", None)]
    candidates = [("trading_symbol_code", "Symbol", None), ("company_name", "Company", None), ("setup_start_date", "Setup met on", None),
                  ("setup_light", "Setup", None, "light"), ("entry_light", "Entry", None, "light"), ("price_to_sales_ratio", "Price-to-sales", NUMBER2),
                  ("down_week_count", "Weeks down", NUMBER0), ("week_change_ratio", "Week change", PERCENT), ("week_end_date", "Week ending", None)]
    events = [("event_date", "Date", None), ("trading_symbol_code", "Symbol", None), ("event_name", "Event", None),
              ("setup_start_date", "Setup period starts", None), ("entry_number", "Entry no.", NUMBER0),
              ("price_to_sales_ratio", "Price-to-sales", NUMBER2), ("down_week_count", "Weeks down", NUMBER0), ("reason_text", "Why", None)]
    return {"name": "short-selling", "displayName": "Short Selling", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": [
        text("short-title", ["# Strategy 002: Short Selling\n", "\n", "Short expensive stocks that keep falling, only when the market climate is red.\n", "\n",
                             "- Setup: a market climate light is red, price-to-sales is above 15 and the stock closed three weeks in a row down\n",
                             "- Entry: the stock closes its sixth week in a row down while the setup is on (green entry light)\n",
                             "- Exit: close all shorts when the climate leaves red; worst case a 25% move against you, and a 25% trailing stop (both need a position)\n",
                             "- Hold 3 to 5 stocks at a time and risk at most 1% of equity in each\n", "\n",
                             "A stock leaves the list when its price-to-sales falls to 15 or below, or it rises for a week. Change the date at the top."], 0, 0, 12, 7),
        table("short-gate", "Market climate gate", "ds_short_gate", gate, 0, 7, 12, 3),
        table("short-candidates", "Candidates: setups open this week", "ds_short_candidates", candidates, 0, 10, 12, 8,
              "Green setup light: all setup conditions hold. Green entry light: the sixth week down has happened in this setup period."),
        table("short-events", "Latest events", "ds_short_events", events, 0, 18, 12, 9),
        table("short-dates", "Data dates", "ds_strategy_freshness", [("short_week_date", "Week shown (strategy 002)", None), ("climate_date", "Latest market climate", None),
                                                                      ("latest_event_date", "Latest strategy event", None)], 0, 27, 12, 3),
    ]}


def filters_page() -> dict:
    return {"name": "filters", "displayName": "Filters", "pageType": "PAGE_TYPE_GLOBAL_FILTERS", "layoutVersion": "GRID_V1", "layout": [
        filter_widget("filter-as-of", "As of date (latest complete week on or before it)", "filter-date-picker",
                      [(d, "parameter", "as_of_date") for d in DATE_DATASETS], 0, 0, 4)]}


def build() -> str:
    return dashboard_json(dataset_entries(DATASETS, parameters), [bear_page(), fund_page(), short_page(), filters_page()])
