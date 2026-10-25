import pytest

from common.wikipedia_sp500 import parse_constituents

HEADER = (
    "<tr><th>Symbol</th><th>Security</th><th>GICS Sector</th><th>GICS Sub-Industry</th>"
    "<th>Headquarters Location</th><th>Date added</th><th>CIK</th><th>Founded</th></tr>"
)
ROW = (
    "<tr><td><a>BRK.B</a></td><td>Berkshire Hathaway</td><td>Financials</td><td>Insurance</td>"
    "<td>Omaha, Nebraska</td><td>2010-02-16</td><td>1067983</td><td>1839</td></tr>"
)


def page(header=HEADER, rows=ROW, table_id="constituents"):
    return f'<html><body><table id="{table_id}">{header}{rows}</table></body></html>'


def test_row_values_are_text_and_cik_is_padded():
    (record,) = parse_constituents(page())
    assert record["symbol"] == "BRK.B"
    assert record["date_added"] == "2010-02-16"
    assert record["cik"] == "0001067983"
    assert record["founded"] == "1839"


def test_missing_table_fails():
    with pytest.raises(ValueError, match="not found"):
        parse_constituents(page(table_id="other"))


def test_changed_columns_fail():
    with pytest.raises(ValueError, match="unexpected columns"):
        parse_constituents(page(header=HEADER.replace("CIK", "Central Index Key")))
