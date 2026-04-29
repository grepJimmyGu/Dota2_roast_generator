"""
Common tag rules — apply to all roles.

Maps to spec: packages/core/analysis/tag_rules/common.py
"""
from __future__ import annotations
from dota_core.roast.tag_rules import safe_get

# Configurable thresholds
_T = {
    "high_death_per_min":        0.22,   # deaths/min above this = high death rate
    "high_death_abs":            8,      # deaths above this always flags
    "low_impact_win_score":      44,     # won but scored below → low_impact_win
    "low_impact_loss_score":     40,     # lost and scored below → low_impact_loss
    "low_participation_kpm":     0.12,   # (kills+assists)/min below this → low participation
    "low_objective_dmg":         1500,   # tower_damage below this
    "low_hero_damage_per_min":   300,    # hero_damage/min below this
    "comeback_early_score":      60,     # early score above this + lost = thrower
    "comeback_late_score":       45,     # late score below this + lost + high early = thrower
    "good_stats_kda":            3.0,    # KDA above this but low score = good_stats_low_impact
    "good_stats_low_score":      48,
    "late_spike_early_max":      45,     # early score low
    "late_spike_mid_max":        45,     # mid score low
    "late_spike_late_min":       58,     # but late score higher = power spike came late
}


def tag_common(player: dict, match_context: dict) -> list[str]:
    """Return common tag_ids applicable to any role based on available data."""
    tags: list[str] = []

    deaths      = safe_get(player, "deaths")
    duration    = safe_get(player, "duration_min", 1.0)
    won         = safe_get(player, "won")
    score       = safe_get(player, "overall_score")
    kills       = safe_get(player, "kills", 0)
    assists     = safe_get(player, "assists", 0)
    tower_dmg   = safe_get(player, "tower_damage")
    hero_dmg    = safe_get(player, "hero_damage")
    early_score = safe_get(player, "early_position_score")
    late_score  = safe_get(player, "late_position_score")
    mid_score   = safe_get(player, "mid_position_score")

    # high_death
    if deaths is not None and duration > 0:
        if deaths >= _T["high_death_abs"] or (deaths / duration) >= _T["high_death_per_min"]:
            tags.append("high_death")

    # low_impact_win
    if won is True and score is not None and score < _T["low_impact_win_score"]:
        tags.append("low_impact_win")

    # low_impact_loss
    if won is False and score is not None and score < _T["low_impact_loss_score"]:
        tags.append("low_impact_loss")

    # low_teamfight_participation — proxy via (kills+assists)/min
    if kills is not None and assists is not None and duration > 0:
        kpm = (kills + assists) / duration
        if kpm < _T["low_participation_kpm"]:
            tags.append("low_teamfight_participation")

    # fed_enemy_core — proxy: early phase was bad + deaths are high
    if early_score is not None and deaths is not None:
        if early_score < 38 and deaths >= 5:
            tags.append("fed_enemy_core")

    # comeback_thrower — had good early but lost
    if won is False and early_score is not None and late_score is not None:
        if early_score > _T["comeback_early_score"] and late_score < _T["comeback_late_score"]:
            tags.append("comeback_thrower")

    # low_objective_damage
    if tower_dmg is not None and tower_dmg < _T["low_objective_dmg"]:
        tags.append("low_objective_damage")

    # low_hero_damage
    if hero_dmg is not None and duration > 0:
        if (hero_dmg / duration) < _T["low_hero_damage_per_min"]:
            tags.append("low_hero_damage")

    # late_power_spike — early/mid weak but late high (roles: carry, mid, offlane)
    position = safe_get(player, "position", 0)
    if position in {1, 2, 3} and early_score is not None and mid_score is not None and late_score is not None:
        if (early_score < _T["late_spike_early_max"]
                and mid_score < _T["late_spike_mid_max"]
                and late_score > _T["late_spike_late_min"]):
            tags.append("late_power_spike")

    # good_stats_low_impact — decent KDA but poor overall score
    if kills is not None and deaths is not None and score is not None:
        deaths_safe = max(deaths, 1)
        kda = (kills + assists) / deaths_safe
        if kda > _T["good_stats_kda"] and score < _T["good_stats_low_score"]:
            tags.append("good_stats_low_impact")

    return tags
