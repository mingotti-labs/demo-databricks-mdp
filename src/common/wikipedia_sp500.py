# Fetch helper for Wikipedia's "List of S&P 500 companies" -- scoped to that one
# page's `constituents` table, not a generic HTML scraper.
import re

import requests
from lxml import html

EXPECTED_COLUMNS = [
    "symbol",
    "security",
    "gics_sector",
    "gics_sub_industry",
    "headquarters_location",
    "date_added",
    "cik",
    "founded",
]


def parse_constituents(page: str) -> list[dict]:
    """Parse the `constituents` table into rows of text, CIK zero-padded to 10 digits.

    Every value stays text exactly as shown (symbols keep their dots, dates are
    not parsed). Fails if the table or any expected column is missing, so a
    layout change stops the pipeline instead of loading wrong data.
    """
    tables = html.fromstring(page).xpath('//table[@id="constituents"]')
    if not tables:
        raise ValueError("table with id 'constituents' not found")
    rows = tables[0].xpath(".//tr")
    names = [
        re.sub(r"\W+", "_", th.text_content().strip().lower()).strip("_")
        for th in rows[0].xpath("./th")
    ]
    if names != EXPECTED_COLUMNS:
        raise ValueError(f"unexpected columns: {names}")
    records = []
    for row in rows[1:]:
        cells = [td.text_content().strip() for td in row.xpath("./td")]
        record = dict(zip(names, cells, strict=True))
        record["cik"] = record["cik"].zfill(10)
        records.append(record)
    return records


def fetch_constituents(url: str, user_agent: str) -> list[dict]:
    """GET the page with a contact User-Agent (Wikimedia policy) and parse it."""
    response = requests.get(url, headers={"User-Agent": user_agent}, timeout=60)
    response.raise_for_status()
    return parse_constituents(response.text)
