"""
Stratz GraphQL HTTP transport layer.
All API calls in the project go through query() here.
"""
from __future__ import annotations
import httpx
from dota_core.config import STRATZ_ENDPOINT, STRATZ_TOKEN

_HEADERS: dict[str, str] = {
    "Authorization": f"Bearer {STRATZ_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


def query(gql: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL query against the Stratz API. Raises on HTTP or GraphQL errors."""
    payload: dict = {"query": gql}
    if variables:
        payload["variables"] = variables

    response = httpx.post(STRATZ_ENDPOINT, json=payload, headers=_HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "errors" in data:
        raise ValueError(f"GraphQL errors: {data['errors']}")

    return data["data"]
