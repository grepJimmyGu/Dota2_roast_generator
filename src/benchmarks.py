# DEPRECATED: split into src/dota_core/benchmarks/{fetch,transform,priors}.py
from __future__ import annotations
from functools import lru_cache

from src.stratz_client import query
from src.queries import HERO_BENCHMARKS, POSITION_BENCHMARKS
from src.constants import LANE_END, MID_END, POSITION_STRATZ

# Stratz bracketBasicIds enum values — grouped pairs
_RANK_TO_BRACKET = [
    (25,  "HERALD_GUARDIAN"),
    (45,  "CRUSADER_ARCHON"),
    (65,  "LEGEND_ANCIENT"),
    (999, "DIVINE_IMMORTAL"),
]


def rank_to_bracket(average_rank: int | None) -> str:
    """
    Convert Stratz's averageRank (e.g. 44 = Archon 4) to a bracketBasicIds enum string.
    Defaults to CRUSADER_ARCHON if rank is unknown.
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
    Fetch real public match averages for a hero, bracket, position, and time window.
    All five dimensions are cached — same combo is only fetched once per session.
    """
    pos_str = POSITION_STRATZ.get(position)
    data = query(
        HERO_BENCHMARKS,
        {
            "heroId":         hero_id,
            "bracketBasicIds": [bracket],
            "positionIds":    [pos_str] if pos_str else None,
            "minTime":        min_time,
            "maxTime":        max_time,
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
    Fetch public match averages for ALL heroes at a position+bracket+time window.
    Used for position score (hero-agnostic role execution benchmark).
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
    Fetch hero AND position benchmarks for all three phases.
    Returns {phase: {"hero": bm, "position": bm}}.
    """
    bracket = rank_to_bracket(average_rank)
    closing_end = max(duration_min, MID_END + 1)

    phases = {
        "lane":    (0,        LANE_END),
        "mid":     (LANE_END, MID_END),
        "closing": (MID_END,  closing_end),
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
