# Fetch helpers for SEC EDGAR's ticker list and XBRL company facts -- scoped to
# those two endpoints, not a generic EDGAR client. Rows are written as JSON Lines
# into the source's volume by src/common/fetch_sec.py; Auto Loader appends them.
import hashlib
import json
import time

import requests

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
FACT_FIELDS = ["start", "end", "val", "accn", "fy", "fp", "form", "filed", "frame"]


class SecClient:
    """GET with a contact User-Agent, at most `per_second` requests a second (SEC policy)."""

    def __init__(self, user_agent: str, per_second: int = 10):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self.gap = 1 / per_second
        self.last = 0.0

    def get(self, url: str) -> requests.Response:
        wait = self.last + self.gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.last = time.monotonic()
        return self.session.get(url, timeout=60)

    def tickers(self) -> dict:
        response = self.get(TICKERS_URL)
        response.raise_for_status()
        return response.json()

    def facts(self, cik: str) -> dict | None:
        """Company facts for a 10-digit CIK, or None when SEC has none (404)."""
        response = self.get(FACTS_URL.format(cik=cik))
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()


def text(value) -> str | None:
    """Keep a value as SEC sent it, as text; missing stays missing."""
    return None if value is None else str(value)


def ticker_rows(payload: dict) -> list[dict]:
    """One row per entry of company_tickers.json, CIK zero-padded to 10 digits."""
    return [
        {"cik": str(row["cik_str"]).zfill(10), "ticker": row["ticker"], "title": row["title"]}
        for row in payload.values()
    ]


def fact_rows(cik: str, payload: dict, concepts: set[tuple[str, str]]) -> list[dict]:
    """One row per reported value of a mapped (taxonomy, concept), values as text."""
    rows = []
    for taxonomy, items in payload.get("facts", {}).items():
        for concept, body in items.items():
            if (taxonomy, concept) not in concepts:
                continue
            for unit, values in body["units"].items():
                for value in values:
                    row = {
                        "cik": cik,
                        "entity_name": payload.get("entityName"),
                        "taxonomy": taxonomy,
                        "concept": concept,
                        "unit": unit,
                    }
                    row.update({field: text(value.get(field)) for field in FACT_FIELDS})
                    rows.append(row)
    return rows


def content_sha256(rows: list[dict]) -> str:
    """Hash of the rows, independent of their order, so an unchanged company hashes the same."""
    lines = sorted(json.dumps(row, sort_keys=True) for row in rows)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def stamp(rows: list[dict], ingested: str, sha: str | None = None) -> list[dict]:
    """Add the fetch time (and the content hash for facts) to every row."""
    extra = {"ingested_timestamp": ingested}
    if sha is not None:
        extra["content_sha256"] = sha
    return [row | extra for row in rows]


def to_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row) + "\n" for row in rows)
