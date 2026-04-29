# DEPRECATED: moved to src/dota_core/domain/heroes.py
from __future__ import annotations
from functools import lru_cache
from src.stratz_client import query

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
    return _fetch_hero_names().get(hero_id, f"Hero#{hero_id}")
