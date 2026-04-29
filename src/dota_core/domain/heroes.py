"""
Hero name resolution via live Stratz constants query.
Result is cached in-process for the session lifetime.

TODO: replace with a static JSON asset or DB table to avoid a cold-start API call.
"""
from __future__ import annotations
from functools import lru_cache
from dota_core.client import query

_HERO_NAME_QUERY = """
query {
  constants {
    heroes {
      id
      displayName
    }
  }
}
"""


@lru_cache(maxsize=1)
def _fetch_hero_names() -> dict[int, str]:
    data = query(_HERO_NAME_QUERY, {})
    return {h["id"]: h["displayName"] for h in data["constants"]["heroes"]}


def hero_name(hero_id: int) -> str:
    """Return the display name for a hero ID, e.g. hero_name(1) → 'Anti-Mage'."""
    return _fetch_hero_names().get(hero_id, f"Hero#{hero_id}")
