"""Widgets and constants shared by the generated dashboards (openspec market-climate-dashboard,
inflation-deflation-monitor): tables, filters, counters, Vega-Lite charts, parameters and the theme."""

import json

from common.market_climate_queries import MONTHS_SHOWN

RED, YELLOW, GREEN = "#E15759", "#F2C037", "#59A14F"
INK = "#11171C"
TEXT_COLOR = {"expr": "colors.textPrimary.default"}
START_DATE = {"expr": f"datetime(year(now()), month(now()) - {MONTHS_SHOWN - 1}, 1)"}
AXIS_WIDTH = 64
Y_PADDING = 14
MONTH_END = {"expr": "datetime(year(now()), month(now()) + 1, 1)"}
SHARED_DOMAIN = [START_DATE, MONTH_END]
TIME_AXIS = {"tickCount": {"interval": "month", "step": 3}, "labelOverlap": True,
             "labelExpr": "month(datum.value) == 0 ? timeFormat(datum.value, '%b %y') : timeFormat(datum.value, '%b')"}
PALETTE = ["#4E79A7", "#F28E2C", "#76B7B2", "#59A14F", "#B07AA1", "#E15759", "#F2C037"]
LIGHT_POSITIONS = {"red": 5, "yellow": 6, "green": 3}

NUMBER2 = {"type": "number", "decimalPlaces": {"type": "exact", "places": 2}}
NUMBER4 = {"type": "number", "decimalPlaces": {"type": "exact", "places": 4}}
NUMBER0 = {"type": "number", "decimalPlaces": {"type": "exact", "places": 0}}
PERCENT = {"type": "number-percent", "decimalPlaces": {"type": "exact", "places": 2}}


def date_parameter() -> dict:
    """The dashboard's date: defaults to today; the queries take the latest day on or before it."""
    return {"keyword": "as_of_date", "displayName": "As of date", "dataType": "DATE",
            "defaultSelection": {"values": {"dataType": "DATE", "values": [{"value": "now/d"}]}}}


def string_parameter(keyword: str, display_name: str, default: str) -> dict:
    return {"keyword": keyword, "displayName": display_name, "dataType": "STRING",
            "defaultSelection": {"values": {"dataType": "STRING", "values": [{"value": default}]}}}


def dataset_entries(queries: dict[str, tuple[str, str]], parameters) -> list[dict]:
    """Dashboard datasets from {name: (title, query)}; `parameters(name)` lists a dataset's parameters."""
    out = []
    for name, (title, query) in queries.items():
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


def counter(name: str, title: str, dataset: str, field: str, fmt: dict, x: int, y: int, w: int, h: int) -> dict:
    return {"widget": {"name": name,
                       "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": [{"name": field, "expression": f"`{field}`"}], "disaggregated": True}}],
                       "spec": {"version": 2, "widgetType": "counter", "encodings": {"value": {"fieldName": field, "displayName": title, "format": fmt}},
                                "frame": {"showTitle": True, "title": title}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


BLUE = "#4E79A7"
BAND_SCALE = {"domain": ["red", "yellow", "green", "blue"], "range": [RED, YELLOW, GREEN, BLUE]}
SCHEMA = "https://vega.github.io/schema/vega-lite/v6.json"
BASE = {"$schema": SCHEMA, "data": {"name": "databricks_query"}, "width": "container", "height": "container",
        "config": {"autosize": {"type": "fit", "contains": "padding"}}}


def custom(name: str, dataset: str, fields: list[str], spec: dict, x: int, y: int, w: int, h: int, title: str | None = None) -> dict:
    """A Vega-Lite widget without the standard title bar (the title is drawn inside when `spec` has one)."""
    return {"widget": {"name": name,
                       "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": [{"name": n, "expression": f"`{n}`"} for n in fields], "disaggregated": True}}],
                       "spec": {"version": 1, "widgetType": "custom-vega-viz", "jsonSpec": {"type": "vega-lite", "spec": json.dumps({**BASE, **spec})},
                                "encodings": {"fields": [{"fieldName": n} for n in fields]}, "data": {"queryName": "main_query"},
                                "frame": {"showTitle": bool(title), **({"title": title} if title else {})}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


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


def dashboard_json(datasets: list[dict], pages: list[dict]) -> str:
    """The file content of a .lvdash.json with the shared theme."""
    dashboard = {
        "datasets": datasets,
        "pages": pages,
        "uiSettings": {"theme": {
            "canvasBackgroundColor": {"light": "#FCFCFC", "dark": "#1F272D"},
            "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#11171C"},
            "fontColor": {"light": "#11171C", "dark": "#E8ECF0"},
            "selectionColor": {"light": "#2272B4", "dark": "#8ACAFF"},
            "visualizationColors": PALETTE,
            "widgetHeaderAlignment": "LEFT"}},
    }
    return json.dumps(dashboard, indent=2) + "\n"
