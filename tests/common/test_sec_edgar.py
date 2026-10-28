import json

from common.sec_edgar import content_sha256, fact_rows, stamp, ticker_rows, to_jsonl

FACTS = {
    "cik": 34088,
    "entityName": "EXXON MOBIL CORP",
    "facts": {
        "us-gaap": {
            "PaymentsOfDividends": {
                "units": {
                    "USD": [
                        {
                            "start": "2024-01-01",
                            "end": "2024-12-31",
                            "val": 16704000000,
                            "accn": "0000034088-25-000010",
                            "fy": 2024,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2025-02-19",
                            "frame": "CY2024",
                        }
                    ]
                }
            },
            "Revenues": {"units": {"USD": [{"end": "2024-12-31", "val": 1}]}},
        },
        "dei": {
            "EntityCommonStockSharesOutstanding": {
                "units": {
                    "shares": [
                        {
                            "end": "2025-01-31",
                            "val": 4345000000,
                            "accn": "0000034088-25-000010",
                            "fy": 2024,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2025-02-19",
                        }
                    ]
                }
            }
        },
    },
}
CONCEPTS = {("us-gaap", "PaymentsOfDividends"), ("dei", "EntityCommonStockSharesOutstanding")}


def test_only_mapped_concepts_in_long_form_as_text():
    rows = fact_rows("0000034088", FACTS, CONCEPTS)
    assert {r["concept"] for r in rows} == {
        "PaymentsOfDividends",
        "EntityCommonStockSharesOutstanding",
    }
    dividends = next(r for r in rows if r["concept"] == "PaymentsOfDividends")
    assert dividends["val"] == "16704000000"
    assert dividends["fy"] == "2024"
    assert dividends["unit"] == "USD"
    assert dividends["entity_name"] == "EXXON MOBIL CORP"


def test_point_in_time_value_has_no_start():
    rows = fact_rows("0000034088", FACTS, CONCEPTS)
    shares = next(r for r in rows if r["taxonomy"] == "dei")
    assert shares["start"] is None
    assert shares["frame"] is None


def test_hash_ignores_row_order_and_sees_a_change():
    rows = fact_rows("0000034088", FACTS, CONCEPTS)
    assert content_sha256(rows) == content_sha256(list(reversed(rows)))
    changed = [dict(rows[0], val="1")] + rows[1:]
    assert content_sha256(changed) != content_sha256(rows)


def test_tickers_are_padded():
    payload = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
    assert ticker_rows(payload) == [{"cik": "0000320193", "ticker": "AAPL", "title": "Apple Inc."}]


def test_stamped_rows_round_trip_as_json_lines():
    rows = stamp(
        ticker_rows({"0": {"cik_str": 1, "ticker": "A", "title": "A"}}),
        "2026-10-28T00:00:00Z",
        "abc",
    )
    (line,) = to_jsonl(rows).splitlines()
    assert json.loads(line) == {
        "cik": "0000000001",
        "ticker": "A",
        "title": "A",
        "ingested_timestamp": "2026-10-28T00:00:00Z",
        "content_sha256": "abc",
    }
