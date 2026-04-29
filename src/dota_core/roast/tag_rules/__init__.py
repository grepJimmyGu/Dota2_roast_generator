"""
Tag rule functions — one module per role.

Each exposes a tag_<role>(player: dict, match_context: dict) -> list[str] function.
Rules only fire when required evidence fields are present in the player dict.

player dict keys (from PlayerMatchStats):
  kills, deaths, assists, duration_min, won
  overall_score, position_score, hero_score
  early_position_score, mid_position_score, late_position_score
  hero_damage, tower_damage, net_worth, gold_per_min, last_hits
  weaknesses, strengths, position, hero_name

match_context is currently the same dict — reserved for future per-match context
(e.g. team networth delta, enemy hero list, item timestamps).
"""
from __future__ import annotations


def safe_get(d: dict, key: str, default=None):
    """Return d[key] if present and not None, else default."""
    val = d.get(key)
    return default if val is None else val
