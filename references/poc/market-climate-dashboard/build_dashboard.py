"""Builds src/dashboards/market_climate.lvdash.json from queries.py (openspec market-climate-dashboard).

Usage: uv run python references/poc/market-climate-dashboard/build_dashboard.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from queries import DATASETS  # noqa: E402

OUT = Path(__file__).resolve().parents[3] / "src" / "dashboards" / "market_climate.lvdash.json"
DATE_DATASETS = [
    "ds_freshness", "ds_lights", "ds_answers", "ds_index_day", "ds_top_up", "ds_top_down", "ds_excluded",
    "ds_members", "ds_checks", "ds_company_check", "ds_company_price", "ds_company_figures", "ds_sectors", "ds_sector_up", "ds_sector_down",
]
SECTOR_DATASETS = ["ds_sector_up", "ds_sector_down"]
COMPANY_DATASETS = ["ds_company_check", "ds_company_price", "ds_company_figures"]
RANGE_DATASETS = ["ds_company_price"]
RED, YELLOW, GREEN = "#E15759", "#F2C037", "#59A14F"
PALETTE = ["#4E79A7", "#F28E2C", "#76B7B2", "#59A14F", "#B07AA1", "#E15759", "#F2C037"]
LIGHT_POSITIONS = {"red": 5, "yellow": 6, "green": 3}

NUMBER2 = {"type": "number", "decimalPlaces": {"type": "exact", "places": 2}}
NUMBER4 = {"type": "number", "decimalPlaces": {"type": "exact", "places": 4}}
NUMBER0 = {"type": "number", "decimalPlaces": {"type": "exact", "places": 0}}
PERCENT = {"type": "number-percent", "decimalPlaces": {"type": "exact", "places": 2}}


def parameters(dataset: str) -> list[dict]:
    result = []
    if dataset in DATE_DATASETS:
        result.append({
            "keyword": "as_of_date", "displayName": "As of date", "dataType": "DATE",
            "defaultSelection": {"values": {"dataType": "DATE", "values": [{"value": "now/d"}]}},
        })
    if dataset in SECTOR_DATASETS:
        result.append({
            "keyword": "sector_name", "displayName": "Sector", "dataType": "STRING",
            "defaultSelection": {"values": {"dataType": "STRING", "values": [{"value": "Information Technology"}]}},
        })
    if dataset in COMPANY_DATASETS:
        result.append({
            "keyword": "company_name", "displayName": "Company", "dataType": "STRING",
            "defaultSelection": {"values": {"dataType": "STRING", "values": [{"value": "EQT Corporation"}]}},
        })
    if dataset in RANGE_DATASETS:
        result.append({
            "keyword": "range_code", "displayName": "Range", "dataType": "STRING",
            "defaultSelection": {"values": {"dataType": "STRING", "values": [{"value": "6M"}]}},
        })
    return result


def datasets() -> list[dict]:
    out = []
    for name, (title, query) in DATASETS.items():
        entry = {"name": name, "displayName": title, "queryLines": [query]}
        if parameters(name):
            entry["parameters"] = parameters(name)
        out.append(entry)
    return out


def text(name: str, lines: list[str], x: int, y: int, w: int, h: int) -> dict:
    return {"widget": {"name": name, "multilineTextboxSpec": {"lines": lines}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def table(name: str, title: str, dataset: str, columns: list[tuple], x: int, y: int, w: int, h: int,
          description: str | None = None) -> dict:
    """columns: (field, display name, format or None, light rule field flag)."""
    fields = [{"name": c[0], "expression": f"`{c[0]}`"} for c in columns]
    encodings = []
    for c in columns:
        column = {"fieldName": c[0], "displayName": c[1], "alignContent": "left"}
        if c[2]:
            column["format"] = c[2]
        if len(c) > 3 and c[3] == "light":
            column["style"] = {"type": "basic", "rules": [
                {"condition": {"operand": {"type": "data-value", "value": color}, "operator": "=="},
                 "backgroundColor": {"themeColorType": "visualizationColors", "position": position}}
                for color, position in LIGHT_POSITIONS.items()]}
        encodings.append(column)
    frame = {"showTitle": True, "title": title}
    if description:
        frame.update({"showDescription": True, "description": description})
    return {"widget": {"name": name,
                       "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": fields, "disaggregated": True}}],
                       "spec": {"version": 2, "widgetType": "table", "encodings": {"columns": encodings}, "frame": frame}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def line(name: str, title: str, dataset: str, x_field: str, y_fields: list[tuple], x: int, y: int, w: int, h: int,
         color_field: str | None = None, mappings: list[dict] | None = None, annotations: list[dict] | None = None,
         description: str | None = None) -> dict:
    fields = [{"name": x_field, "expression": f"`{x_field}`"}]
    fields += [{"name": f, "expression": f"`{f}`"} for f, _ in y_fields]
    encodings = {"x": {"fieldName": x_field, "scale": {"type": "temporal"}, "displayName": "Date"}}
    if len(y_fields) == 1:
        encodings["y"] = {"fieldName": y_fields[0][0], "scale": {"type": "quantitative"}, "displayName": y_fields[0][1]}
    else:
        encodings["y"] = {"scale": {"type": "quantitative"},
                          "fields": [{"fieldName": f, "displayName": d} for f, d in y_fields]}
    if color_field:
        fields.append({"name": color_field, "expression": f"`{color_field}`"})
        scale = {"type": "categorical"}
        if mappings:
            scale["mappings"] = mappings
        encodings["color"] = {"fieldName": color_field, "scale": scale}
    frame = {"showTitle": True, "title": title}
    if description:
        frame.update({"showDescription": True, "description": description})
    spec = {"version": 3, "widgetType": "line", "encodings": encodings, "frame": frame}
    if annotations:
        spec["annotations"] = annotations
    return {"widget": {"name": name,
                       "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": fields, "disaggregated": True}}],
                       "spec": spec},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def bar(name: str, title: str, dataset: str, category: str, value: tuple, x: int, y: int, w: int, h: int) -> dict:
    fields = [{"name": category, "expression": f"`{category}`"}, {"name": value[0], "expression": f"`{value[0]}`"}]
    encodings = {"x": {"fieldName": category, "scale": {"type": "categorical", "sort": {"by": "y-reversed"}}, "displayName": "Sector"},
                 "y": {"fieldName": value[0], "scale": {"type": "quantitative"}, "displayName": value[1]}}
    return {"widget": {"name": name,
                       "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": fields, "disaggregated": True}}],
                       "spec": {"version": 3, "widgetType": "bar", "encodings": encodings,
                                "frame": {"showTitle": True, "title": title}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def horizontal(value: str, label: str, color: str) -> dict:
    return {"type": "horizontal-line", "encodings": {"y": {"dataValue": value, "dataType": "INTEGER"},
                                                      "label": {"value": label}, "color": {"value": color}}}


def filter_widget(name: str, title: str, kind: str, bindings: list[tuple[str, str, str]], x: int, y: int, w: int) -> dict:
    """bindings: (dataset, 'field'|'parameter', name)."""
    queries, fields = [], []
    for dataset, mode, ref in bindings:
        qname = f"q_{dataset}_{ref}"
        query = {"datasetName": dataset, "disaggregated": False}
        if mode == "parameter":
            query["parameters"] = [{"name": ref, "keyword": ref}]
            fields.append({"parameterName": ref, "queryName": qname})
        else:
            query["fields"] = [{"name": ref, "expression": f"`{ref}`"}]
            fields.append({"fieldName": ref, "displayName": title, "queryName": qname})
        queries.append({"name": qname, "query": query})
    return {"widget": {"name": name, "queries": queries,
                       "spec": {"version": 2, "widgetType": kind, "encodings": {"fields": fields},
                                "frame": {"showTitle": True, "title": title}}},
            "position": {"x": x, "y": y, "width": w, "height": 2}}


def traffic_lights(name: str, x: int, y: int, w: int, h: int) -> dict:
    """Big coloured circle per climate (custom Vega-Lite), driven by ds_lights."""
    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v6.json", "data": {"name": "databricks_query"},
        "width": "container", "height": "container", "config": {"autosize": {"type": "fit", "contains": "padding"}},
        "transform": [{"calculate": "datum.yes_count + '/3'", "as": "yes_label"}],
        "encoding": {"x": {"field": "lens_name", "type": "nominal", "axis": {"title": None, "orient": "top", "labelFontSize": 18, "labelAngle": 0, "domain": False, "ticks": False}},
                     "tooltip": [{"field": "lens_name", "title": "Climate"}, {"field": "action_name", "title": "Action"}, {"field": "reason_text", "title": "Why"}]},
        "layer": [
            {"mark": {"type": "circle", "size": 14000},
             "encoding": {"y": {"value": 95}, "color": {"field": "light_code", "type": "nominal", "legend": None,
                          "scale": {"domain": ["red", "yellow", "green"], "range": [RED, YELLOW, GREEN]}}}},
            {"mark": {"type": "text", "fontSize": 22, "fontWeight": "bold", "color": "#11171C"},
             "encoding": {"y": {"value": 95}, "text": {"field": "yes_label"}}},
        ],
    }
    names = ["lens_name", "yes_count", "light_code", "action_name", "reason_text"]
    return {"widget": {"name": name,
                       "queries": [{"name": "main_query", "query": {"datasetName": "ds_lights", "fields": [{"name": n, "expression": f"`{n}`"} for n in names], "disaggregated": True}}],
                       "spec": {"version": 1, "widgetType": "custom-vega-viz", "jsonSpec": {"type": "vega-lite", "spec": json.dumps(spec)},
                                "encodings": {"fields": [{"fieldName": n} for n in names]}, "data": {"queryName": "main_query"},
                                "frame": {"showTitle": True, "title": "Market climate today"}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def vega(name: str, title: str, dataset: str, fields: list[str], spec: dict, x: int, y: int, w: int, h: int,
         description: str | None = None) -> dict:
    spec = {"$schema": "https://vega.github.io/schema/vega-lite/v6.json", "data": {"name": "databricks_query"},
            "width": "container", "height": "container", "config": {"autosize": {"type": "fit", "contains": "padding"}}, **spec}
    frame = {"showTitle": True, "title": title}
    if description:
        frame.update({"showDescription": True, "description": description})
    return {"widget": {"name": name,
                       "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": [{"name": n, "expression": f"`{n}`"} for n in fields], "disaggregated": True}}],
                       "spec": {"version": 1, "widgetType": "custom-vega-viz", "jsonSpec": {"type": "vega-lite", "spec": json.dumps(spec)},
                                "encodings": {"fields": [{"fieldName": n} for n in fields]}, "data": {"queryName": "main_query"}, "frame": frame}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def light_history(x: int, y: int, w: int, h: int) -> dict:
    """Both climates; the long-run line is drawn wide and pale under the thin modern line so equal answers stay visible."""
    time_x = {"field": "signal_date", "type": "temporal", "title": None}
    spec = {"encoding": {"x": time_x, "y": {"field": "yes_count", "type": "quantitative", "title": "Yes answers", "scale": {"domain": [0, 3]}, "axis": {"tickMinStep": 1}},
                         "color": {"field": "lens_name", "type": "nominal", "title": "Climate"},
                         "tooltip": [{"field": "signal_date", "type": "temporal", "title": "Day"}, {"field": "lens_name", "title": "Climate"}, {"field": "yes_count", "title": "Yes answers"}]},
            "layer": [{"transform": [{"filter": "datum.lens_code == 'long_run'"}], "mark": {"type": "line", "strokeWidth": 9, "opacity": 0.35, "interpolate": "step-after"}},
                      {"transform": [{"filter": "datum.lens_code == 'modern'"}], "mark": {"type": "line", "strokeWidth": 2.5, "interpolate": "step-after"}}]}
    return vega("light-history", "Yes answers per day (0 green, 1 yellow, 2 or 3 red)", "ds_light_history",
                ["signal_date", "lens_name", "lens_code", "yes_count"], spec, x, y, w, h,
                "Both climates are drawn; where the wide pale line shows around the thin one, they gave the same answer.")


def fed_history(x: int, y: int, w: int, h: int) -> dict:
    """Target rate line over a background: red within 6 months of a hike, green within 6 months of a cut."""
    time_x = {"field": "signal_date", "type": "temporal", "title": None}
    spec = {"layer": [
        {"transform": [{"window": [{"op": "lead", "field": "signal_date", "as": "next_date"}], "sort": [{"field": "signal_date"}]},
                       {"filter": "datum.fed_band_code == 'red' || datum.fed_band_code == 'green'"}],
         "mark": {"type": "rect", "opacity": 0.22},
         "encoding": {"x": time_x, "x2": {"field": "next_date"}, "y": {"value": 0}, "y2": {"value": {"expr": "height"}},
                      "color": {"field": "fed_band_code", "type": "nominal", "title": "Fed",
                                "scale": {"domain": ["red", "green"], "range": [RED, GREEN]},
                                "legend": {"labelExpr": "datum.value == 'red' ? 'in the way (hike)' : 'out of the way (cut)'"}}}},
        {"mark": {"type": "line", "interpolate": "step-after", "strokeWidth": 2.5, "color": "#2B3A55"},
         "encoding": {"x": time_x, "y": {"field": "fed_target_rate", "type": "quantitative", "title": "Target rate (%)", "scale": {"zero": False}},
                      "tooltip": [{"field": "signal_date", "type": "temporal", "title": "Day"}, {"field": "fed_target_rate", "title": "Target rate (%)"}]}}]}
    return vega("fed-history", "Fed target rate (upper limit), percent", "ds_fed_history", ["signal_date", "fed_target_rate", "fed_band_code"], spec, x, y, w, h,
                "Red background: within 6 months of a hike. Green background: within 6 months of a cut.")


def counter(name: str, title: str, dataset: str, field: str, fmt: dict, x: int, y: int, w: int, h: int) -> dict:
    return {"widget": {"name": name,
                       "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": [{"name": field, "expression": f"`{field}`"}], "disaggregated": True}}],
                       "spec": {"version": 2, "widgetType": "counter", "encodings": {"value": {"fieldName": field, "displayName": title, "format": fmt}},
                                "frame": {"showTitle": True, "title": title}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


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
        line("company-price", "Close with Bollinger bands", "ds_company_price", "price_date",
             [("price_close", "Close"), ("band_upper", "Upper band"), ("band_middle", "20-day average"), ("band_lower", "Lower band")], 0, 9, 12, 8),
        table("company-steps", "From the numbers to the P/E", "ds_company_check", steps, 0, 17, 12, 10),
    ]}


def climate_page() -> dict:
    lights = [("lens_name", "Climate", None), ("yes_count", "Yes answers (of 3)", NUMBER0),
              ("light_code", "Light", None, "light"), ("action_name", "Action", None), ("reason_text", "Why", None)]
    answers = [("lens_name", "Climate", None), ("signal_name", "Question", None), ("answer_text", "Answer", None),
               ("band_code", "Band", None, "light"), ("measured_value", "Measured", NUMBER2),
               ("threshold_value", "Compared with", NUMBER2), ("reason_text", "Why", None)]
    dates = [("climate_date", "Climate as of", None), ("sp500_price_date", "Latest S&P 500 price", None),
             ("fed_rate_date", "Latest Fed target reading", None), ("cpi_date", "Latest CPI reading (monthly, carried forward)", None)]
    mapping = [{"value": "red", "color": RED}, {"value": "yellow", "color": YELLOW}, {"value": "green", "color": GREEN}]
    return {"name": "climate", "displayName": "Climate", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": [
        text("climate-title", ["# Market Climate\n", "\n", "Two climates read the same three questions. Yes is the unfavourable answer.\n", "\n", "- Is the market too expensive?\n", "- Is the Fed in the way?\n", "- Is the market going up?\n", "\n", "- Red (2 or 3 yes): sell\n", "- Yellow (1 yes): buy and hold\n", "- Green (0 yes): strong buy\n", "\n", "Change the date at the top. The other pages show the numbers behind the valuation answer."], 0, 0, 12, 5),
        traffic_lights("traffic-lights", 0, 5, 12, 6),
        light_history(0, 11, 12, 5),
        line("pe-history", "S&P 500 price/earnings ratio", "ds_pe_history", "valuation_date",
             [("pe_ten_year_adjusted", "10-year inflation-adjusted (votes)"), ("pe_trailing", "Trailing 12 months")], 0, 16, 12, 6,
             annotations=[horizontal("16", "cheap line, long run", GREEN), horizontal("22", "expensive line, long run", YELLOW),
                          horizontal("30", "expensive line, modern", RED)],
             description="Price over earnings of the current members. Valuation answer: too expensive above 22 (long run) or 30 (modern)."),
        fed_history(0, 22, 12, 6),
        line("trend-history", "S&P 500 and its 200-day average", "ds_trend_history", "signal_date",
             [("sp500_close", "S&P 500 close"), ("sp500_average_200", "200-day average")], 0, 28, 12, 6),
        table("answers", "The three answers of each climate", "ds_answers", answers, 0, 34, 12, 7),
        table("lights", "Lights of the day", "ds_lights", lights, 0, 41, 12, 3),
        table("data-dates", "Data dates", "ds_freshness", dates, 0, 44, 12, 3,
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
        bar("sector-pe", "Sector P/E", "ds_sectors", "sector_name", ("sector_pe", "Sector P/E"), 0, 10, 12, 5),
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


def main() -> None:
    dashboard = {
        "datasets": datasets(),
        "pages": [climate_page(), deep_dive_page(), company_page(), sector_page(), filters_page()],
        "uiSettings": {"theme": {
            "canvasBackgroundColor": {"light": "#FCFCFC", "dark": "#1F272D"},
            "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#11171C"},
            "fontColor": {"light": "#11171C", "dark": "#E8ECF0"},
            "selectionColor": {"light": "#2272B4", "dark": "#8ACAFF"},
            "visualizationColors": PALETTE,
            "widgetHeaderAlignment": "LEFT"}},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dashboard, indent=2) + "\n", encoding="utf-8")
    print("wrote", OUT, len(dashboard["datasets"]), "datasets")


if __name__ == "__main__":
    main()
