"""P3: can the Wikipedia S&P 500 page be parsed into the fields the story needs?"""

import re
from io import StringIO

import pandas as pd
import requests

URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
HEADERS = {"User-Agent": "mdp handsonessential@gmail.com"}


def main() -> None:
    html = requests.get(URL, headers=HEADERS, timeout=30).text
    constituents = pd.read_html(
        StringIO(html), attrs={"id": "constituents"}, flavor="lxml"
    )[0]
    print("rows", len(constituents))
    print("columns", list(constituents.columns))
    print(constituents.head(3).to_string())

    cik = constituents["CIK"].astype(str)
    print(
        "CIK null",
        constituents["CIK"].isna().sum(),
        "lengths",
        cik.str.len().value_counts().to_dict(),
    )
    added = pd.to_datetime(constituents["Date added"], errors="coerce")
    print(
        "date added unparsed",
        added.isna().sum(),
        "min",
        added.min(),
        "max",
        added.max(),
    )
    print(
        "symbols with a dot",
        constituents.loc[constituents["Symbol"].str.contains(r"\."), "Symbol"].tolist(),
    )
    shared = constituents[constituents.duplicated("CIK", keep=False)].sort_values("CIK")
    print(
        "CIKs with more than one symbol",
        shared[["Symbol", "Security", "CIK"]].to_string(index=False),
    )
    print("distinct CIK", constituents["CIK"].nunique())

    print("table tags", re.findall(r"<table[^>]*>", html))


main()
