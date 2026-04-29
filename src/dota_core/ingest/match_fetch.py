"""
Per-match detail fetching: per-minute stat arrays for a single player in a match.
"""
from __future__ import annotations
import time

from dota_core.client import query
from dota_core.ingest.queries import MATCH_DETAILED
from dota_core.ingest.player_fetch import _parse_position, _sum_list


def get_match_detail(match_id: int, steam_account_id: int) -> dict | None:
    """
    Fetch per-minute stat arrays for a single match.

    Returns a merged dict combining match-level context with the player's stats block:
      {match_id, duration_seconds, average_rank, won, radiant_kills, dire_kills,
       heroId, position, isRadiant, assists, stats}

    Returns None if the match is unparsed or unavailable.
    """
    data = query(MATCH_DETAILED, {"matchId": match_id, "steamAccountId": steam_account_id})
    match = data.get("match")
    if not match or not match.get("players"):
        return None

    player = match["players"][0]
    is_radiant = player.get("isRadiant")
    did_radiant_win = match.get("didRadiantWin")
    won = (is_radiant == did_radiant_win) if (is_radiant is not None and did_radiant_win is not None) else None

    return {
        "match_id":        match.get("id") or match_id,
        "duration_seconds": match.get("durationSeconds"),
        "average_rank":    match.get("averageRank"),
        "won":             won,
        "radiant_kills":   _sum_list(match.get("radiantKills")),
        "dire_kills":      _sum_list(match.get("direKills")),
        # player fields
        "heroId":          player.get("heroId"),
        "position":        _parse_position(player.get("position")),
        "isRadiant":       is_radiant,
        "assists":         player.get("assists"),
        "deaths":          player.get("deaths"),
        "stats":           player.get("stats"),
    }


def get_match_details(
    match_ids: list[int],
    steam_account_id: int,
    delay: float = 0.3,
) -> dict[int, dict | None]:
    """
    Fetch per-minute stat arrays for multiple matches.
    Returns {match_id: player_detail_dict}.
    """
    details: dict[int, dict | None] = {}
    for match_id in match_ids:
        details[match_id] = get_match_detail(match_id, steam_account_id)
        time.sleep(delay)
    return details
