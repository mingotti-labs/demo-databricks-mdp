"""Builds the Currency Monitor dashboard JSON from its dataset queries (openspec currency-monitor).

`build()` returns the file content of `src/dashboards/currency_monitor.lvdash.json`; `cicd/build_dashboards.py` writes it
and a test checks the committed file equals it. Same date axis, colours and theme as the other dashboards.
"""

from common.dashboard_widgets import (
    AXIS_WIDTH,
    BAND_SCALE,
    INK,
    NUMBER0,
    NUMBER2,
    PALETTE,
    PERCENT,
    GREEN,
    RED,
    SHARED_DOMAIN,
    TEXT_COLOR,
    TIME_AXIS,
    Y_PADDING,
    custom,
    dashboard_json,
    dataset_entries,
    date_parameter,
    filter_widget,
    range_time_x,
    string_parameter,
    table,
    text,
    time_lines,
    vega,
    with_range_dates,
)
from common.currency_queries import DATASETS, US_SHORT_YIELDS
from common.market_climate_queries import DATASETS as CLIMATE_DATASETS

DATE_DATASETS = ["ds_currency_freshness", "ds_dollar", "ds_currency_grid", "ds_currency_distance", "ds_country_rates", "ds_yield_ranking"]
CURRENCY_DATASETS = ["ds_currency_history", "ds_currency_rates_history"]
DATASETS = {**DATASETS, "ds_history_range_options": CLIMATE_DATASETS["ds_history_range_options"]}


def parameters(dataset: str) -> list[dict]:
    result = [date_parameter()] if dataset in DATE_DATASETS else []
    if dataset in CURRENCY_DATASETS:
        result.append(string_parameter("currency_code", "Currency", "CHF"))
    if dataset == "ds_yield_ranking":
        result.append(string_parameter("base_code", "Base currency", "AUD"))
    if dataset == "ds_us_yield_curve":
        result.append(string_parameter("history_range_code", "History range", "36M"))
    return result


def dollar_tiles(x: int, y: int, w: int, h: int) -> dict:
    """The two dollar indexes of the day: a circle each, green when the dollar is strong (above its 200-day average and rising), red when weak."""
    spec = {
        "title": {"text": {"expr": "'The dollar as of ' + utcFormat(toDate(data('databricks_query')[0].signal_date), '%Y-%m-%d')"},
                  "anchor": "start", "fontSize": 16, "color": TEXT_COLOR},
        "encoding": {"x": {"field": "signal_name", "type": "nominal", "sort": {"field": "index_order"},
                           "axis": {"title": None, "orient": "bottom", "labelFontSize": 15, "labelAngle": 0, "labelColor": TEXT_COLOR, "domain": False, "ticks": False}},
                     "tooltip": [{"field": "signal_name", "title": "Index"}, {"field": "reason_text", "title": "Why"}]},
        "layer": [
            {"mark": {"type": "circle", "size": 14000},
             "encoding": {"y": {"value": 90}, "color": {"field": "dollar_band", "type": "nominal", "legend": None, "scale": BAND_SCALE}}},
            {"mark": {"type": "text", "fontSize": 22, "fontWeight": "bold", "color": INK},
             "encoding": {"y": {"value": 90}, "text": {"field": "dollar_state"}}},
        ],
    }
    return custom("dollar-tiles", "ds_dollar", ["signal_date", "signal_name", "index_order", "dollar_state", "dollar_band", "reason_text"], spec, x, y, w, h)


def distance_bars(x: int, y: int, w: int, h: int) -> dict:
    """How far each currency is from its 200-day average, against the US dollar and against the Australian dollar."""
    spec = {"mark": {"type": "bar"},
            "encoding": {"y": {"field": "currency_name", "type": "nominal", "sort": {"field": "currency_order"}, "title": None},
                         "yOffset": {"field": "base_label", "type": "nominal"},
                         "x": {"field": "distance_ratio", "type": "quantitative", "title": "Distance from the 200-day average (positive: gaining)",
                               "axis": {"format": ".0%"}, "scale": {"padding": Y_PADDING}},
                         "color": {"field": "base_label", "type": "nominal", "title": None, "legend": {"orient": "top"}},
                         "tooltip": [{"field": "currency_name", "title": "Currency"}, {"field": "base_label", "title": "Against"},
                                     {"field": "distance_ratio", "type": "quantitative", "format": ".1%", "title": "Distance"}]}}
    return custom("distance-bars", "ds_currency_distance", ["currency_name", "currency_order", "base_label", "distance_ratio"], spec, x, y, w, h,
                  "How far each currency is from its 200-day average")


def rate_lines(x: int, y: int, w: int, h: int) -> dict:
    """The short-term rate and the 10-year yield of the chosen currency's country (the 10-year when it has one)."""
    time_x = {"field": "indicator_date", "type": "temporal", "title": None, "scale": {"domain": SHARED_DOMAIN}, "axis": TIME_AXIS}
    spec = {"mark": {"type": "line", "strokeWidth": 2, "interpolate": "step-after"},
            "encoding": {"x": time_x,
                         "y": {"field": "rate_value", "type": "quantitative", "title": "Percent", "scale": {"zero": False, "padding": Y_PADDING},
                               "axis": {"format": ".2f", "minExtent": AXIS_WIDTH}},
                         "color": {"field": "rate_label", "type": "nominal", "title": None, "legend": {"orient": "top"}},
                         "tooltip": [{"field": "indicator_date", "type": "temporal", "title": "Day"}, {"field": "rate_label", "title": "Rate"},
                                     {"field": "rate_value", "type": "quantitative", "format": ".2f", "title": "Percent"}]}}
    return custom("rate-lines", "ds_currency_rates_history", ["indicator_date", "rate_label", "rate_value"], spec, x, y, w, h,
                  "Short-term rate and 10-year yield of the currency's country (monthly readings are carried forward)")


def currency_monitor_page() -> dict:
    grid = [("currency_name", "Currency", None), ("value_in_usd", "Value in US dollars", NUMBER2), ("against_usd", "Against the US dollar", None),
            ("band_usd", "Band", None, "light"), ("distance_usd", "From 200-day average", PERCENT),
            ("value_in_aud", "Value in Australian dollars", NUMBER2), ("against_aud", "Against the Australian dollar", None),
            ("band_aud", "Band", None, "light"), ("distance_aud", "From 200-day average", PERCENT)]
    rates = [("country_currency", "Country (currency)", None), ("short_term_rate", "Short-term rate, %", NUMBER2), ("short_term_date", "Reading of", None),
             ("short_term_note", "Note", None), ("ten_year_yield", "10-year yield, %", NUMBER2), ("ten_year_date", "Reading of", None),
             ("ten_year_note", "Note", None)]
    dates = [("currency_date", "Currency Monitor as of", None), ("dollar_index_date", "Latest US Dollar Index", None),
             ("broad_index_date", "Latest broad dollar index", None), ("exchange_rate_date", "Latest exchange rate (weekly from FRED)", None)]
    return {"name": "currency-monitor", "displayName": "Currency Monitor", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": [
        text("currency-title", ["# Currency Monitor\n", "\n", "Is the dollar strong or weak, and which main currencies are gaining or losing against the US dollar and against the Australian dollar?\n", "\n",
                                "- A currency is gaining when its value is above its 200-day average\n", "- The US Dollar Index (DXY) is the dollar's megatrend; the Federal Reserve's broad index covers about 26 currencies\n",
                                "- Each value is worked out from the US dollar rates: a Swiss franc in Australian dollars is the franc in US dollars divided by the Australian dollar in US dollars\n",
                                "- Interest rates: the short-term rate and the 10-year yield of each country, with the date of the reading\n", "\n",
                                "Change the date at the top. A dollar index above its average is a strong dollar (green: gaining), at or below it a weak dollar (red)."], 0, 0, 12, 6),
        dollar_tiles(0, 6, 12, 6),
        time_lines("dollar-history", "The dollar indexes and their 200-day averages", "ds_dollar_history", "indicator_date",
                   [("dxy_close", "US Dollar Index (DXY)"), ("dxy_average", "DXY 200-day average"), ("broad_value", "Broad dollar index"),
                    ("broad_average", "Broad 200-day average")], "Index points", 0, 12, 12, 6, ",.1f"),
        table("currency-grid", "Currencies against the US dollar and the Australian dollar", "ds_currency_grid", grid, 0, 18, 12, 9),
        distance_bars(0, 27, 12, 8),
        table("country-rates", "Interest rates of the main countries", "ds_country_rates", rates, 0, 35, 12, 8,
              "Monthly readings are shown with their date; a note says when a reading is older than 4 months. China has no 10-year yield on FRED."),
        table("currency-dates", "Data dates", "ds_currency_freshness", dates, 0, 43, 12, 3),
    ]}


def deep_dive_page() -> dict:
    return {"name": "currency-deep-dive", "displayName": "Currency Deep Dive", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": [
        text("dive-title", ["# Currency Deep Dive\n", "\n", "Pick a currency: its value in US and Australian dollars against their 200-day averages, "
                            "and the short-term rate and 10-year yield of its country when it has one.\n"], 0, 0, 12, 3),
        filter_widget("filter-currency", "Currency", "filter-single-select",
                      [("ds_currency_options", "field", "currency_code"), ("ds_currency_history", "parameter", "currency_code"),
                       ("ds_currency_rates_history", "parameter", "currency_code")], 0, 3, 6),
        time_lines("currency-history", "Value of one unit of the currency", "ds_currency_history", "indicator_date",
                   [("value_in_usd", "In US dollars"), ("average_in_usd", "US dollars, 200-day average"), ("value_in_aud", "In Australian dollars"),
                    ("average_in_aud", "Australian dollars, 200-day average")], "Value of one unit", 0, 5, 12, 7, ",.4f"),
        rate_lines(0, 12, 12, 7),
    ]}


def score_bars(x: int, y: int, w: int, h: int) -> dict:
    """The score of each country: short-term rate plus the 12-month change of its currency against the base."""
    spec = {"mark": {"type": "bar"},
            "encoding": {"y": {"field": "currency_name", "type": "nominal", "sort": {"field": "rank_position"}, "title": None},
                         "x": {"field": "short_plus_12m", "type": "quantitative", "title": "Short-term rate plus 12-month currency change, percent",
                               "scale": {"padding": Y_PADDING}},
                         "color": {"condition": {"test": "datum.short_plus_12m > 0", "value": GREEN}, "value": RED},
                         "tooltip": [{"field": "currency_name", "title": "Currency"}, {"field": "short_term_rate", "title": "Short-term rate, %"},
                                     {"field": "currency_change_12m", "title": "12-month change, %"}, {"field": "short_plus_12m", "title": "Total, %"}]}}
    return custom("score-bars", "ds_yield_ranking", ["rank_position", "currency_name", "short_term_rate", "currency_change_12m", "short_plus_12m"],
                  spec, x, y, w, h, "Short-term rate plus the 12-month change of the currency")


def us_yield_chart(x: int, y: int, w: int, h: int) -> dict:
    """The US 10-year yield against the chosen short-term US yields; the 10-year repeats on each maturity's rows, so it is
    drawn from one row per day."""
    time_x = range_time_x("observation_date")
    names = [name for _, name, _ in US_SHORT_YIELDS]
    colour = {"field": "series_name", "type": "nominal", "title": "Short-term yield",
              "scale": {"domain": names, "range": PALETTE[1:5]}}
    value_y = {"field": "yield_value", "type": "quantitative", "title": "Yield, percent",
               "scale": {"zero": False, "padding": Y_PADDING}, "axis": {"format": ".2f", "minExtent": AXIS_WIDTH}}
    day = {"field": "observation_date", "type": "temporal", "title": "Day"}
    spec = {"layer": [
        {"transform": [{"filter": "datum.series_name == '10-year'"},
                       {"aggregate": [{"op": "max", "field": "yield_value", "as": "yield_value"}], "groupby": ["observation_date"]}],
         "mark": {"type": "line", "strokeWidth": 2.6, "color": INK},
         "encoding": {"x": time_x, "y": value_y,
                      "tooltip": [day, {"field": "yield_value", "type": "quantitative", "format": ".2f", "title": "10-year yield, %"}]}},
        {"transform": [{"filter": "datum.series_name != '10-year'"}],
         "mark": {"type": "line", "strokeWidth": 1.8},
         "encoding": {"x": time_x, "y": value_y, "color": colour,
                      "tooltip": [day, {"field": "series_name", "title": "Short-term yield"},
                                  {"field": "yield_value", "type": "quantitative", "format": ".2f", "title": "Yield, %"},
                                  {"field": "spread", "type": "quantitative", "format": ".2f", "title": "10-year minus it, points"}]}},
    ]}
    return vega("us-yield-chart", "US 10-year Treasury yield against short-term US yields", "ds_us_yield_curve",
                ["observation_date", "maturity_name", "series_name", "yield_value", "spread", "range_start_date", "range_end_date"],
                with_range_dates(spec), x, y, w, h,
                "Black: the 10-year. Pick one or several short-term yields; the tooltip gives the gap to the 10-year in percentage points.")


def yield_page() -> dict:
    ranking = [("rank_position", "Rank", NUMBER0), ("currency_name", "Currency", None), ("short_term_rate", "Short-term rate, %", NUMBER2),
               ("short_term_date", "Reading of", None), ("ten_year_yield", "10-year yield, %", NUMBER2),
               ("currency_change_12m", "Currency change, last 12 months, %", NUMBER2), ("distance_from_average", "From 200-day average, %", NUMBER2),
               ("short_plus_12m", "Short-term rate + 12-month change, %", NUMBER2)]
    return {"name": "yield-deep-dive", "displayName": "Yield Deep Dive", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": [
        text("yield-title", ["# Yield Deep Dive\n", "\n", "Which country would have paid the most, in your base currency? Each country is ranked by its short-term interest rate "
                             "plus the change of its currency against the base over the last 12 months (252 trading days).\n", "\n",
                             "- Pick the base currency: the Australian dollar or the US dollar\n",
                             "- The currency change looks backward; it is not a forecast, and high-rate currencies often fall\n",
                             "- The rates are interbank or policy rates, not what a bank pays on a CD; the date of each reading is shown\n",
                             "- The base currency is shown with no currency change\n"], 0, 0, 12, 5),
        filter_widget("filter-base", "Base currency", "filter-single-select",
                      [("ds_base_options", "field", "base_code"), ("ds_yield_ranking", "parameter", "base_code")], 0, 7, 6),
        table("yield-ranking", "Countries ranked by short-term rate plus 12-month currency change", "ds_yield_ranking", ranking, 0, 9, 12, 9),
        score_bars(0, 18, 12, 7),
        filter_widget("filter-maturity", "Short-term US yields", "filter-multi-select", [("ds_us_yield_curve", "field", "maturity_name")], 0, 25, 6),
        filter_widget("filter-yield-range", "History range", "filter-single-select",
                      [("ds_history_range_options", "field", "history_range_code"), ("ds_us_yield_curve", "parameter", "history_range_code")], 6, 25, 6),
        us_yield_chart(0, 27, 12, 9),
    ]}


def filters_page() -> dict:
    return {"name": "filters", "displayName": "Filters", "pageType": "PAGE_TYPE_GLOBAL_FILTERS", "layoutVersion": "GRID_V1", "layout": [
        filter_widget("filter-as-of", "As of date (latest day on or before it)", "filter-date-picker",
                      [(d, "parameter", "as_of_date") for d in DATE_DATASETS], 0, 0, 4)]}


def build() -> str:
    return dashboard_json(dataset_entries(DATASETS, parameters), [currency_monitor_page(), deep_dive_page(), yield_page(), filters_page()])
