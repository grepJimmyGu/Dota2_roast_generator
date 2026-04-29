# DEPRECATED: split into src/dota_core/ingest/player_fetch.py and match_fetch.py
from __future__ import annotations
import time
import pandas as pd
from src.stratz_client import query
from src.queries import (
    PLAYER_RANKED_MATCHES,
    MATCH_DETAILED,
    PLAYER_HERO_PERFORMANCE,
    PLAYER_INFO,
)
from src.benchmarks import get_benchmarks_for_match


def get_player_info(steam_account_id: int) -> dict:
    data = query(PLAYER_INFO, {"steamAccountId": steam_account_id})
    return data["player"]


def _sum_list(val):
    """Sum a list (per-minute array) or return the value as-is if already scalar."""
    if isinstance(val, list):
        return sum(val)
    return val


def _parse_position(pos) -> int | None:
    """Convert Stratz position string ('POSITION_3') to int (3), or pass through int."""
    if pos is None:
        return None
    if isinstance(pos, int):
        return pos
    try:
        return int(str(pos).split("_")[-1])
    except (ValueError, IndexError):
        return None


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
                "heroId":   player_stats.get("heroId"),
                "position": _parse_position(player_stats.get("position")),
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


def get_match_detail(match_id: int, steam_account_id: int) -> dict | None:
    """
    Fetch per-minute stat arrays for a single match.
    Returns the player's stats dict, or None if unavailable.
    """
    data = query(MATCH_DETAILED, {"matchId": match_id, "steamAccountId": steam_account_id})
    match = data.get("match")
    if not match or not match.get("players"):
        return None
    return match["players"][0]


def get_match_details(
    match_ids: list[int],
    steam_account_id: int,
    delay: float = 0.3,
) -> dict[int, dict | None]:
    """
    Fetch per-minute stat arrays for multiple matches.
    Returns {match_id: player_detail_dict}.
    """
    details = {}
    for match_id in match_ids:
        details[match_id] = get_match_detail(match_id, steam_account_id)
        time.sleep(delay)
    return details


def get_benchmarks_for_matches(df: pd.DataFrame) -> dict[int, dict | None]:
    """
    Fetch hero benchmarks for each match in the DataFrame (cached per hero/week/bracket).
    Returns {match_id: benchmark_dict}.
    """
    benchmarks = {}
    for _, row in df.iterrows():
        benchmarks[row["match_id"]] = get_benchmarks_for_match(
            hero_id=int(row["heroId"]),
            match_start_time=int(row["start_time"]),
            average_rank=row.get("average_rank"),
        )
    return benchmarks


def get_hero_performance(steam_account_id: int) -> pd.DataFrame:
    """Fetch aggregated ranked performance per hero for a player."""
    data = query(PLAYER_HERO_PERFORMANCE, {"steamAccountId": steam_account_id})
    heroes = data["player"]["heroesPerformance"]
    return pd.DataFrame(heroes)
