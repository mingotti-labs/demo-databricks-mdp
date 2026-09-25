# Shared fetch helper for ISO 3166 country/subdivision reference data --
# scoped to this one source system's two static CSV files, not a generic
# any-CSV framework.
import csv
import io

import requests


def fetch_iso3166_csv(url: str) -> list[dict]:
    """GET an ISO 3166 CSV file and return its rows as dicts.

    Both source files (countries.csv, subdivisions.csv) are plain,
    unauthenticated HTTPS downloads with no pagination, no WAF/User-Agent
    block (confirmed via real requests before this was written -- unlike
    UNGM/ACNC/NSW Spatial's APIs). The header row is prefixed with `#`
    (e.g. `#country_code_alpha2,country_code_alpha3,...`), which the CSV
    module would otherwise treat as a literal column name -- stripped here
    before parsing.
    """
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    text = response.text.lstrip()
    if text.startswith("#"):
        text = text[1:]
    return list(csv.DictReader(io.StringIO(text)))
