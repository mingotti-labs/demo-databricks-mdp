# Shared fetch helper for the UNGM (United Nations Global Marketplace) API
# -- scoped to this one source system, not a generic any-API framework.
# Reusable for future UNGM endpoints beyond UNSPSC.
import requests


def fetch_ungm_endpoint(base_url: str, path: str, auth_token: str | None = None) -> list[dict]:
    """GET an UNGM API endpoint and return its parsed JSON records.

    auth_token is currently unused by every endpoint this project calls
    (UNSPSC is public, no auth) -- present so a future authenticated UNGM
    endpoint can reuse this helper without restructuring it. A real token
    would be retrieved with
    `dbutils.secrets.get("ungm", "api_token")` (matching this project's
    existing secret-scope naming convention) and passed in here; no such
    scope exists yet, and none is created speculatively.
    """
    # UNGM's WAF blocks requests' default User-Agent string with a 403 --
    # confirmed via a real request (reproducible locally: curl's default UA
    # gets 200, python-requests' default UA gets 403 on the identical URL).
    # Not a cloud-IP block, not an auth issue -- purely the UA string.
    headers = {"User-Agent": "curl/8.0"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    response = requests.get(f"{base_url}{path}", headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()["value"]
