# Shared fetch helper for AirROI's short-term rental market intelligence
# API -- scoped to this one source system, not a generic any-API
# framework. Safe to import from src/common/ (not inlined) since this is
# a plain function called driver-side inside a Materialized View body,
# not a custom Spark DataSource class -- the sys.path/ModuleNotFoundError
# constraint found for ACNC's and NSW property's connectors only applies
# to DataSource classes registered via spark.dataSource.register().
import requests


def fetch_market_summary(
    base_url: str, api_key: str, country: str, region: str, locality: str
) -> dict:
    """POST AirROI's /markets/summary endpoint for one market, return parsed JSON.

    AirROI has no free sandbox -- every call costs real money. Callers
    should batch/minimize calls rather than retry casually.

    The request body is a nested `market` object with `country`, `region`,
    and `locality` fields -- confirmed via a real 422 response, not the
    flat country_code/state/city shape shown (incorrectly, for this
    endpoint) in AirROI's own published example.
    """
    response = requests.post(
        f"{base_url}/markets/summary",
        headers={"X-API-KEY": api_key},
        json={"market": {"country": country, "region": region, "locality": locality}},
        timeout=60,
    )
    if not response.ok:
        raise requests.exceptions.HTTPError(
            f"{response.status_code} error for {country}/{region}/{locality}: {response.text}",
            response=response,
        )
    return response.json()
