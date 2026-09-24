# Shared fetch helper for AirROI's short-term rental market intelligence
# API -- scoped to this one source system, not a generic any-API
# framework. Safe to import from src/common/ (not inlined) since this is
# a plain function called driver-side inside a Materialized View body,
# not a custom Spark DataSource class -- the sys.path/ModuleNotFoundError
# constraint found for ACNC's and NSW property's connectors only applies
# to DataSource classes registered via spark.dataSource.register().
import requests


def _market_object(country: str, region: str, locality: str, district: str | None = None) -> dict:
    """Build AirROI's nested `market` object -- country/region/locality are
    always required; district is optional, used for sub-localities that
    aren't their own tracked locality on AirROI (e.g. Cumuruxatiba, a
    district of Prado, not a standalone market)."""
    obj = {"country": country, "region": region, "locality": locality}
    if district:
        obj["district"] = district
    return obj


def _post(base_url: str, api_key: str, path: str, market: dict) -> dict:
    response = requests.post(
        f"{base_url}{path}",
        headers={"X-API-KEY": api_key},
        json={"market": market},
        timeout=60,
    )
    if not response.ok:
        raise requests.exceptions.HTTPError(
            f"{response.status_code} error for {market} on {path}: {response.text}",
            response=response,
        )
    return response.json()


def fetch_market_summary(
    base_url: str,
    api_key: str,
    country: str,
    region: str,
    locality: str,
    district: str | None = None,
) -> dict:
    """POST AirROI's /markets/summary endpoint for one market, return parsed JSON.

    AirROI has no free sandbox -- every call costs real money. Callers
    should batch/minimize calls rather than retry casually.

    The request body is a nested `market` object with `country`, `region`,
    and `locality` fields -- confirmed via a real 422 response, not the
    flat country_code/state/city shape shown (incorrectly, for this
    endpoint) in AirROI's own published example.
    """
    return _post(base_url, api_key, "/markets/summary", _market_object(country, region, locality, district))


def fetch_market_metrics_all(
    base_url: str,
    api_key: str,
    country: str,
    region: str,
    locality: str,
    district: str | None = None,
) -> dict:
    """POST AirROI's /markets/metrics/all endpoint for one market, return
    parsed JSON -- the time-series counterpart to /markets/summary's
    single current snapshot (occupancy/ADR/RevPAR/etc. history, not just
    a current value). Same cost/retry caveats as fetch_market_summary."""
    return _post(base_url, api_key, "/markets/metrics/all", _market_object(country, region, locality, district))
