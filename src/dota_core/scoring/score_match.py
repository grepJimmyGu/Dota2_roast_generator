"""
Match scoring orchestration — single match and batch (DataFrame) variants.
"""
from __future__ import annotations
import pandas as pd

from dota_core.scoring.weights import PHASE_WEIGHTS, PHASE_OVERALL_WEIGHTS
from dota_core.scoring.features import extract_phase_stats
from dota_core.scoring.adjusters import game_closeness, benchmark_multiplier, weighted_score, score_breakdown
from dota_core.benchmarks.transform import build_phase_benchmarks, apply_multiplier


def score_match(
    match_row: dict,
    player_detail: dict | None,
    phase_benchmarks: dict[str, dict[str, dict | None]],
) -> dict[str, float | None]:
    """
    Compute per-phase position and hero scores for a single match, normalized for game state.

    Args:
        match_row:        flat match dict (one row from get_ranked_matches() DataFrame)
        player_detail:    per-minute stat arrays from get_match_detail()
        phase_benchmarks: {phase: {"hero": bm, "position": bm}} from get_phase_benchmarks()

    Returns dict with keys:
        {lane,mid,closing}_{position,hero}_score,
        overall_{position,hero}_score,
        game_closeness
    """
    position     = max(1, min(5, int(match_row.get("position") or 1)))
    duration_sec = match_row.get("duration_seconds") or 0
    hero_id      = int(match_row.get("heroId") or 0)
    won          = match_row.get("won")

    result: dict = {
        "early_game_position_score": None, "early_game_hero_score": None,
        "mid_game_position_score":   None, "mid_game_hero_score":   None,
        "late_game_position_score":  None, "late_game_hero_score":  None,
        "overall_position_score":    None, "overall_hero_score":    None,
        "game_closeness":            None,
        # Per-stat signed z-scores for strengths/weaknesses analysis — not serialized to DataFrame
        "_stat_breakdown":           {},
    }

    if not player_detail or not player_detail.get("stats"):
        return result

    closeness  = game_closeness(match_row)
    multiplier = benchmark_multiplier(closeness, won)
    result["game_closeness"] = closeness

    phase_data = extract_phase_stats(player_detail, duration_sec, hero_id=hero_id, position=position)

    pos_scores:  dict[str, float | None] = {}
    hero_scores: dict[str, float | None] = {}

    for phase in ("early_game", "mid_game", "late_game"):
        bm_pair    = phase_benchmarks.get(phase, {})
        raw_hero   = bm_pair.get("hero")
        raw_pos    = bm_pair.get("position")
        weights    = PHASE_WEIGHTS[phase][position]
        stats      = phase_data[phase]

        pos_bm  = apply_multiplier(build_phase_benchmarks(raw_pos,  phase, position), multiplier) if raw_pos  else None
        hero_bm = apply_multiplier(build_phase_benchmarks(raw_hero, phase, position), multiplier) if raw_hero else None

        pos_scores[phase]  = weighted_score(stats, pos_bm,  weights) if pos_bm  else None
        hero_scores[phase] = weighted_score(stats, hero_bm, weights) if hero_bm else None

        result[f"{phase}_position_score"] = pos_scores[phase]
        result[f"{phase}_hero_score"]     = hero_scores[phase]

        # Collect breakdown using position benchmark (broader signal); fall back to hero bm
        bm_for_breakdown = pos_bm or hero_bm
        if bm_for_breakdown:
            result["_stat_breakdown"][phase] = score_breakdown(stats, bm_for_breakdown, weights)

    for label, score_map in (("position", pos_scores), ("hero", hero_scores)):
        valid = {p: s for p, s in score_map.items() if s is not None}
        if valid:
            w_sum = sum(PHASE_OVERALL_WEIGHTS[p] for p in valid)
            result[f"overall_{label}_score"] = round(
                sum(PHASE_OVERALL_WEIGHTS[p] * s for p, s in valid.items()) / w_sum, 2
            )

    return result


def score_matches(
    df: pd.DataFrame,
    detail_map: dict[int, dict],
    phase_benchmark_map: dict[int, dict[str, dict[str, dict | None]]],
) -> pd.DataFrame:
    """
    Add position/hero scores and game_closeness columns to a matches DataFrame.

    Args:
        df:                  matches DataFrame from get_ranked_matches()
        detail_map:          {match_id: player_detail_dict}
        phase_benchmark_map: {match_id: {phase: {"hero": bm, "position": bm}}}
    """
    df = df.copy()
    scores = df.apply(
        lambda row: score_match(
            row.to_dict(),
            detail_map.get(row["match_id"]),
            phase_benchmark_map.get(row["match_id"], {}),
        ),
        axis=1,
        result_type="expand",
    )
    return pd.concat([df, scores], axis=1)
