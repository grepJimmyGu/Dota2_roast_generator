"""
Game-state adjustments and core scoring math (z-score engine).
"""
from __future__ import annotations


def _zscore(value: float | None, avg: float | None, std: float | None) -> float | None:
    """Compute z-score, clamped to [-3, 3]."""
    if value is None or avg is None or std is None or std == 0:
        return None
    return max(-3.0, min(3.0, (value - avg) / std))


def _scale(z: float) -> float:
    """Map z-score range [-3, 3] → [0, 100]."""
    return round((z + 3) / 6 * 100, 2)


def weighted_score(
    stats: dict[str, float | None],
    benchmarks: dict,
    weights: dict[str, float],
) -> float | None:
    """
    Compute a weighted z-score performance score in [0, 100].

    stats:      {stat_key: player_value}
    benchmarks: {stat_key: {"avg": float, "stdDev": float}}
    weights:    {stat_key: weight}  — negative weight = lower is better
    """
    total_weight = 0.0
    weighted_sum = 0.0

    for stat, weight in weights.items():
        player_val = stats.get(stat)
        bm  = benchmarks.get(stat, {})
        avg = bm.get("avg")
        std = bm.get("stdDev")

        z = _zscore(player_val, avg, std)
        if z is None:
            continue

        weighted_sum += weight * z
        total_weight += abs(weight)

    if total_weight == 0:
        return None

    return _scale(weighted_sum / total_weight)


def score_breakdown(
    stats: dict[str, float | None],
    benchmarks: dict,
    weights: dict[str, float],
) -> dict[str, float]:
    """
    Return per-stat signed z-scores for strengths/weaknesses analysis.

    For stats with negative weight (lower-is-better, e.g. vacancy_time),
    the sign is flipped so that a positive value always means "performed well."

    Returns {stat_key: signed_zscore} for stats with available benchmark data.
    Missing stats (no benchmark or no player value) are omitted.
    """
    result: dict[str, float] = {}
    for stat, weight in weights.items():
        player_val = stats.get(stat)
        bm  = benchmarks.get(stat, {})
        avg = bm.get("avg")
        std = bm.get("stdDev")
        z = _zscore(player_val, avg, std)
        if z is None:
            continue
        # Negative weight = lower is better; flip sign so callers see positive = good
        result[stat] = round(z * (-1 if weight < 0 else 1), 4)
    return result


def game_closeness(match_row: dict) -> float:
    """
    Measure how one-sided the game was.
    Returns 0.0 (complete stomp) → 1.0 (perfectly even kills).
    Uses kill ratio: min(team_kills, enemy_kills) / max(team_kills, enemy_kills).
    """
    r = match_row.get("radiant_kills") or 0
    d = match_row.get("dire_kills") or 0
    if r + d == 0:
        return 1.0
    return round(min(r, d) / max(r, d), 4)


def benchmark_multiplier(closeness: float, won: bool | None) -> float:
    """
    Scale benchmark expectations based on game state.

    Stomp win  (closeness→0, won=True):  multiplier > 1 — expect more from an easy game
    Stomp loss (closeness→0, won=False): multiplier < 1 — expect less when suppressed
    Close game (closeness→1):            multiplier = 1 — standard benchmark

    Max adjustment ±25%.
    """
    if won is None:
        return 1.0
    stomp_factor = 1.0 - closeness
    direction    = 1.0 if won else -1.0
    return round(1.0 + direction * stomp_factor * 0.25, 4)
