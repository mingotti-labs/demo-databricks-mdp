# Fetch helper for the ISO 10383 market identifier code (MIC) list -- scoped to
# this one CSV, not a generic any-CSV framework.
import csv
import io

import requests

COLUMNS = {
    "MIC": "market_identifier_code",
    "OPERATING MIC": "operating_market_identifier_code",
    "OPRT/SGMT": "operating_or_segment",
    "MARKET NAME-INSTITUTION DESCRIPTION": "market_name",
    "LEGAL ENTITY NAME": "legal_entity_name",
    "LEI": "legal_entity_identifier",
    "MARKET CATEGORY CODE": "market_category_code",
    "ACRONYM": "acronym",
    "ISO COUNTRY CODE (ISO 3166)": "country_code_alpha2",
    "CITY": "city",
    "WEBSITE": "website",
    "STATUS": "status",
    "CREATION DATE": "creation_date",
    "LAST UPDATE DATE": "last_update_date",
    "LAST VALIDATION DATE": "last_validation_date",
    "EXPIRY DATE": "expiry_date",
    "COMMENTS": "comments",
}


def parse_market_identifier_codes(text: str) -> list[dict]:
    """Rows of the MIC CSV under the spelled-out column names.

    Fails when a source column is missing, so an upstream rename is a loud
    failure and not a silently empty column. Columns not in COLUMNS are dropped.
    """
    reader = csv.DictReader(io.StringIO(text))
    missing = [name for name in COLUMNS if name not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"ISO 10383 file is missing columns: {missing}")
    return [{COLUMNS[name]: row[name] for name in COLUMNS} for row in reader]


def fetch_market_identifier_codes(url: str) -> list[dict]:
    """GET the MIC CSV and return its rows.

    The bytes are decoded as UTF-8: the server sends no charset, so
    `response.text` would guess ISO-8859-1 and garble accented names (probe P2,
    references/poc/iso-mic/).
    """
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return parse_market_identifier_codes(response.content.decode("utf-8"))
