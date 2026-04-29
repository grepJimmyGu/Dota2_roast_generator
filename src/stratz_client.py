# DEPRECATED: moved to src/dota_core/client.py — update imports to `from dota_core.client import query`
from __future__ import annotations
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

STRATZ_ENDPOINT = "https://api.stratz.com/graphql"
TOKEN = os.getenv("STRATZ_TOKEN")


_HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


def query(gql: str, variables: dict = None) -> dict:
    headers = _HEADERS
    payload = {"query": gql}
    if variables:
        payload["variables"] = variables

    response = httpx.post(STRATZ_ENDPOINT, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "errors" in data:
        raise ValueError(f"GraphQL errors: {data['errors']}")

    return data["data"]
