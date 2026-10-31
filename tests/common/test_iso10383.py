import pytest

from common.iso10383 import COLUMNS, parse_market_identifier_codes

HEADER = ",".join(f'"{name}"' for name in COLUMNS)


def row(**values):
    return ",".join(f'"{values.get(name, "")}"' for name in COLUMNS)


def test_rows_are_renamed_and_keep_accents():
    text = "\n".join(
        [
            HEADER,
            row(
                **{
                    "MIC": "CSOB",
                    "OPERATING MIC": "CSOB",
                    "OPRT/SGMT": "OPRT",
                    "MARKET NAME-INSTITUTION DESCRIPTION": "ČESKOSLOVENSKÁ OBCHODNÍ BANKA, A.S.",
                    "ISO COUNTRY CODE (ISO 3166)": "CZ",
                    "EXPIRY DATE": "",
                }
            ),
        ]
    )
    [parsed] = parse_market_identifier_codes(text)
    assert parsed["market_identifier_code"] == "CSOB"
    assert parsed["market_name"] == "ČESKOSLOVENSKÁ OBCHODNÍ BANKA, A.S."
    assert parsed["country_code_alpha2"] == "CZ"
    assert parsed["expiry_date"] == ""
    assert set(parsed) == set(COLUMNS.values())


def test_missing_column_fails_and_names_it():
    text = HEADER.replace('"MIC",', "") + "\n"
    with pytest.raises(ValueError, match="MIC"):
        parse_market_identifier_codes(text)


def test_extra_columns_are_dropped():
    text = HEADER + ',"NEW COLUMN"\n' + row(**{"MIC": "XASX"}) + ',"x"\n'
    [parsed] = parse_market_identifier_codes(text)
    assert "NEW COLUMN" not in parsed
    assert parsed["market_identifier_code"] == "XASX"
