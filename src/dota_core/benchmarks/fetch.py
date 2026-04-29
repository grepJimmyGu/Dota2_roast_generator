"""
Bracket-aware benchmark fetching from Stratz heroStats API.
Results are cached in-process per unique (hero, bracket, position, time window) key.

TODO: replace lru_cache with a shared cache (Redis/memcache) for multi-worker deployments.
"""
from __future__ import annotations
from functools import lru_cache

from dota_core.client import query
from dota_core.ingest.queries import HERO_BENCHMARKS, POSITION_BENCHMARKS
from dota_core.constants import LANE_END, MID_END, POSITION_STRATZ

_RANK_TO_BRACKET: list[tuple[int, str]] = [
    (25,  "HERALD_GUARDIAN"),
    (45,  "CRUSADER_ARCHON"),
    (65,  "LEGEND_ANCIENT"),
    (999, "DIVINE_IMMORTAL"),
]


def rank_to_bracket(average_rank: int | None) -> str:
    """
    Convert Stratz's averageRank integer (e.g. 44 = Archon 4) to a bracketBasicIds enum.
    Defaults to CRUSADER_ARCHON when rank is unknown.
    """
    if average_rank is None:
        return "CRUSADER_ARCHON"
    for threshold, bracket in _RANK_TO_BRACKET:
        if average_rank <= threshold:
            return bracket
    return "DIVINE_IMMORTAL"


@lru_cache(maxsize=2048)
def fetch_phase_benchmark(
    hero_id: int,
    bracket: str,
    position: int,
    min_time: int,
    max_time: int,
) -> dict | None:
    """
    Fetch real public match averages for a specific hero, bracket, position, and time window.
    All five dimensions are the cache key — same combination is fetched only once per session.
    """
    pos_str = POSITION_STRATZ.get(position)
    data = query(
        HERO_BENCHMARKS,
        {
            "heroId":          hero_id,
            "bracketBasicIds": [bracket],
            "positionIds":     [pos_str] if pos_str else None,
            "minTime":         min_time,
            "maxTime":         max_time,
        },
    )
    stats_list = data["heroStats"]["stats"]
    return stats_list[0] if stats_list else None


@lru_cache(maxsize=512)
def fetch_position_benchmark(
    bracket: str,
    position: int,
    min_time: int,
    max_time: int,
) -> dict | None:
    """
    Fetch public match averages for ALL heroes at a given position, bracket, and time window.
    Used for the position score track (hero-agnostic role execution benchmark).
    """
    pos_str = POSITION_STRATZ.get(position)
    data = query(
        POSITION_BENCHMARKS,
        {
            "bracketBasicIds": [bracket],
            "positionIds":     [pos_str] if pos_str else None,
            "minTime":         min_time,
            "maxTime":         max_time,
        },
    )
    stats_list = data["heroStats"]["stats"]
    return stats_list[0] if stats_list else None


def get_phase_benchmarks(
    hero_id: int,
    position: int,
    average_rank: int | None,
    duration_min: int,
) -> dict[str, dict[str, dict | None]]:
    """
    Fetch hero AND position benchmarks for all three phases (lane / mid / closing).
    Returns {phase: {"hero": bm, "position": bm}}.
    """
    bracket = rank_to_bracket(average_rank)
    closing_end = max(duration_min, MID_END + 1)

    phases = {
        "early_game": (0,        LANE_END),
        "mid_game":   (LANE_END, MID_END),
        "late_game":  (MID_END,  closing_end),
    }
    return {
        phase: {
            "hero":     fetch_phase_benchmark(hero_id, bracket, position, t0, t1),
            "position": fetch_position_benchmark(bracket, position, t0, t1),
        }
        for phase, (t0, t1) in phases.items()
    }


def get_benchmarks_for_match(
    hero_id: int,
    match_start_time: int,
    average_rank: int | None,
) -> dict | None:
    """Legacy single-benchmark fetch (full game, no phase split). Used by test script."""
    bracket = rank_to_bracket(average_rank)
    return fetch_phase_benchmark(hero_id, bracket, 0, 0, 99)
