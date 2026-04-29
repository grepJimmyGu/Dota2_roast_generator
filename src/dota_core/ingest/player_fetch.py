"""
Player-level data fetching: profile, ranked match list, hero performance.
"""
from __future__ import annotations
import time
import pandas as pd

from dota_core.client import query
from dota_core.ingest.queries import (
    PLAYER_INFO,
    PLAYER_RANKED_MATCHES,
    PLAYER_HERO_PERFORMANCE,
    SEARCH_PLAYERS,
)


def get_player_info(steam_account_id: int) -> dict:
    """Fetch basic profile: name, avatar, match/win counts."""
    data = query(PLAYER_INFO, {"steamAccountId": steam_account_id})
    return data["player"]


def get_ranked_matches(
    steam_account_id: int,
    total: int = 100,
    batch_size: int = 20,
    delay: float = 0.5,
) -> pd.DataFrame:
    """
    Fetch up to `total` ranked matches for a player, paginated.
    Returns a flat DataFrame with one row per match.
    """
    records = []
    skip = 0

    while len(records) < total:
        take = min(batch_size, total - len(records))
        data = query(
            PLAYER_RANKED_MATCHES,
            {"steamAccountId": steam_account_id, "take": take, "skip": skip},
        )
        matches = data["player"]["matches"]
        if not matches:
            break

        for match in matches:
            player_stats = match["players"][0] if match["players"] else {}
            won = (
                match["didRadiantWin"] == player_stats.get("isRadiant")
                if player_stats
                else None
            )
            records.append({
                "match_id":         match["id"],
                "start_time":       match["startDateTime"],
                "duration_seconds": match["durationSeconds"],
                "average_rank":     match.get("averageRank"),
                "radiant_kills":    _sum_list(match.get("radiantKills")),
                "dire_kills":       _sum_list(match.get("direKills")),
                "won":              won,
                "heroId":           player_stats.get("heroId"),
                "position":         _parse_position(player_stats.get("position")),
                **{k: player_stats.get(k) for k in [
                    "kills", "deaths", "assists",
                    "goldPerMinute", "experiencePerMinute",
                    "heroDamage", "heroHealing", "towerDamage",
                    "imp", "award",
                ]},
            })

        skip += take
        if len(matches) < take:
            break
        time.sleep(delay)

    return pd.DataFrame(records)


def search_players(name: str) -> list[dict]:
    """
    Search Stratz for players matching `name`.
    Returns a list of {steamId, playerName, avatarUrl} dicts, empty on any failure.
    """
    try:
        data = query(SEARCH_PLAYERS, {"query": name})
        players = (data.get("search") or {}).get("players") or []
        results = []
        for p in players:
            acct = p.get("steamAccount") or {}
            steam_id = p.get("steamAccountId")
            if steam_id is None:
                continue
            results.append({
                "steamId":    int(steam_id),
                "playerName": acct.get("name"),
                "avatarUrl":  acct.get("avatar"),
            })
        return results
    except Exception:
        return []


def get_hero_performance(steam_account_id: int) -> pd.DataFrame:
    """Fetch aggregated ranked performance per hero for a player."""
    data = query(PLAYER_HERO_PERFORMANCE, {"steamAccountId": steam_account_id})
    heroes = data["player"]["heroesPerformance"]
    return pd.DataFrame(heroes)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sum_list(val) -> int | float | None:
    """Sum a per-minute array, or return scalar as-is."""
    if isinstance(val, list):
        return sum(val)
    return val


def _parse_position(pos) -> int | None:
    """Convert Stratz position string ('POSITION_3') → int (3), or pass through int."""
    if pos is None:
        return None
    if isinstance(pos, int):
        return pos
    try:
        return int(str(pos).split("_")[-1])
    except (ValueError, IndexError):
        return None
