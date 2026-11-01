"""Shared logic of the Silver Domain `silver_domain_investments`.

Plain Python only (no Spark import), so it is unit tested without a cluster. The
pipeline files splice the SQL snippets these functions return into their queries.
"""

import hashlib

IDENTIFIER_SOURCE = "sec"
FAR_FUTURE_DATE = "9999-12-31"
SPECIAL_DIVIDEND_FACTOR = 2
SPECIAL_DIVIDEND_LOOKBACK = 4

# (figure, kind, unit). `instant` figures are balance sheet values dated at the
# filing's period end; `duration` figures are trailing twelve months to it;
# `cover` is the cover-page share count, taken from the filing whatever its date.
FIGURES = [
    ("net_income", "duration", "USD"),
    ("operating_cash_flow", "duration", "USD"),
    ("capex", "duration", "USD"),
    ("dividends_paid", "duration", "USD"),
    ("operating_income", "duration", "USD"),
    ("depreciation_and_amortisation", "duration", "USD"),
    ("interest_expense", "duration", "USD"),
    ("earnings_per_share", "duration", "USD/shares"),
    ("long_term_debt", "instant", "USD"),
    ("short_term_debt", "instant", "USD"),
    ("cash", "instant", "USD"),
    ("current_assets", "instant", "USD"),
    ("total_liabilities", "instant", "USD"),
    ("liabilities_and_equity", "instant", "USD"),
    ("stockholders_equity", "instant", "USD"),
    ("total_equity", "instant", "USD"),
    ("preferred_stock", "instant", "USD"),
    ("shares_outstanding", "cover", "shares"),
]

# Yahoo exchange code to ISO 10383 operating market identifier code (probe P2).
YAHOO_EXCHANGE_TO_MARKET = {
    "NMS": "XNAS",
    "NGM": "XNAS",
    "NCM": "XNAS",
    "NYQ": "XNYS",
    "PCX": "XNYS",
    "ASE": "XNYS",
    "BTS": "XCBO",
    "CXI": "XCBO",
}

# (rate_code, source, series_id, unit); the source is the Landing table's source.
RATES = [
    ("australian_dollar_in_us_dollars", "rba", "FXRUSD", "us_dollars_per_australian_dollar"),
    ("rba_cash_rate_target", "rba", "FIRMMCRTD", "percent"),
    ("us_10_year_treasury_yield", "fred", "DGS10", "percent"),
    ("us_federal_funds_effective_rate", "fred", "DFF", "percent"),
    ("us_federal_funds_target_upper", "fred", "DFEDTARU", "percent"),
    ("us_federal_funds_target_lower", "fred", "DFEDTARL", "percent"),
]


def figure_names() -> list[str]:
    return [figure for figure, _, _ in FIGURES]


def entity_id(*parts: str) -> str:
    """SHA-256 hex of the parts joined by `:`, empty parts skipped (as `concat_ws`)."""
    return hashlib.sha256(":".join(part for part in parts if part).encode("utf-8")).hexdigest()


def entity_id_sql(*columns: str) -> str:
    return f"sha2(concat_ws(':', {', '.join(columns)}), 256)"


def market_code_sql(column: str) -> str:
    """CASE expression mapping Yahoo's exchange code column to the operating market code."""
    whens = " ".join(f"WHEN '{c}' THEN '{m}'" for c, m in YAHOO_EXCHANGE_TO_MARKET.items())
    return f"CASE {column} {whens} END"


def figure_values_sql() -> str:
    """VALUES rows (figure, kind, unit) to join mapped facts to their figure."""
    return ", ".join(f"('{f}', '{k}', '{u}')" for f, k, u in FIGURES)


def rate_values_sql() -> str:
    """VALUES rows (rate_code, source, series_id, unit)."""
    return ", ".join(f"('{c}', '{s}', '{i}', '{u}')" for c, s, i, u in RATES)


def figure_columns_sql() -> str:
    """One column per figure from rows (figure, value): the value when the figure matches."""
    columns = []
    for figure, _, _ in FIGURES:
        value = "CAST(ROUND(value) AS BIGINT)" if figure == "shares_outstanding" else "value"
        columns.append(f"max(CASE WHEN figure = '{figure}' THEN {value} END) AS {figure}")
    return ",\n  ".join(columns)
