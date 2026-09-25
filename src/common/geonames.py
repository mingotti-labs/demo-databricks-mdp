# Shared fetch helpers for GeoNames' public dump files -- scoped to this
# one source system's plain and zip-wrapped static downloads, not a
# generic any-dump-file framework.
#
# None of these files have a header row DictReader can use directly:
# admin1CodesASCII.txt/admin2Codes.txt/cities500.txt have no header at all
# (confirmed via real fetches), and countryInfo.txt's real header is one of
# several `#`-prefixed documentation lines, not reliably the first or last.
# Both helpers take `fieldnames` explicitly rather than trying to parse a
# header out of the file.
import csv
import io
import zipfile

import requests


def fetch_geonames_dump(url: str, fieldnames: list[str]) -> list[dict]:
    """GET a plain tab-delimited GeoNames dump file and return its rows as dicts."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    lines = [line for line in response.text.splitlines() if not line.startswith("#")]
    return list(csv.DictReader(lines, fieldnames=fieldnames, delimiter="\t"))


def fetch_geonames_zip_dump(url: str, inner_filename: str, fieldnames: list[str]) -> list[dict]:
    """GET a zip-wrapped GeoNames dump file and return the named inner file's rows as dicts."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        with archive.open(inner_filename) as inner_file:
            text = inner_file.read().decode("utf-8")
    lines = [line for line in text.splitlines() if not line.startswith("#")]
    return list(csv.DictReader(lines, fieldnames=fieldnames, delimiter="\t"))
