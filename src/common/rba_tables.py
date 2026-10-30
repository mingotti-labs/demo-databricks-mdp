# Helpers for the RBA fetch (src/common/fetch_rba.py): turn an RBA statistical
# table CSV into one row per series and date, and pick the rows to write. No
# network here; the notebook downloads the files and writes the JSON Lines.
import csv
import io
import json
from datetime import date, timedelta

TABLES = {
    "F11.1": "f11.1-data.csv",
    "F1": "f1-data.csv",
    "F2": "f2-data.csv",
    "F5": "f5-data.csv",
}
LOOKBACK_DAYS = 31
MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ],
        1,
    )
}
HEADER_ROWS = {
    "Title": "title",
    "Description": "description",
    "Frequency": "frequency",
    "Type": "type",
    "Units": "units",
    "Source": "source",
    "Publication date": "publication_date",
}


def parse_date(text: str) -> date:
    """`03-Jan-2023` as a date; month names are read here, not by the locale."""
    day, month, year = text.split("-")
    return date(int(year), MONTHS[month], int(day))


def parse_table(table_id: str, content: str) -> list[dict]:
    """Rows of one table: a value per series and date, empty cells skipped.

    The file has one column per series, a block of header rows (title, units,
    ...) ending in `Series ID`, then one row per date. Every value, including the
    date, stays text as the RBA wrote it. Fails when there is no `Series ID` row
    or a data row does not start with a date, so a layout change stops the fetch
    instead of writing wrong rows.
    """
    lines = [r for r in csv.reader(io.StringIO(content.lstrip("﻿"))) if r]
    start = next((i for i, r in enumerate(lines) if r[0] == "Series ID"), None)
    if start is None:
        raise ValueError(f"{table_id}: no 'Series ID' row")
    series = lines[start][1:]
    header = {HEADER_ROWS[r[0]]: r[1:] for r in lines[:start] if r[0] in HEADER_ROWS}
    rows = []
    for line in lines[start + 1 :]:
        parse_date(line[0])
        for column, series_id in enumerate(series):
            value = line[column + 1].strip() if column + 1 < len(line) else ""
            if not value:
                continue
            rows.append(
                {
                    "table_id": table_id,
                    "series_id": series_id,
                    "observation_date": line[0],
                    "value": value,
                    **{
                        name: (values[column] or None) if column < len(values) else None
                        for name, values in header.items()
                    },
                }
            )
    return rows


def first_day(last_stored: date | None, reload: bool) -> date | None:
    """First observation date to write: LOOKBACK_DAYS before the last stored one.

    None writes everything, for a table with no stored rows or a reload.
    """
    if reload or last_stored is None:
        return None
    return last_stored - timedelta(days=LOOKBACK_DAYS)


def since(rows: list[dict], first: date | None) -> list[dict]:
    """Rows dated on or after `first`; all rows when it is None."""
    if first is None:
        return rows
    return [r for r in rows if parse_date(r["observation_date"]) >= first]


def stamp(rows: list[dict], ingested: str) -> list[dict]:
    """Add the fetch time to every row."""
    return [row | {"ingested_timestamp": ingested} for row in rows]


def to_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row) + "\n" for row in rows)
