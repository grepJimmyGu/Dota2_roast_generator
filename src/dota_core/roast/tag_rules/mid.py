"""Mid (Pos 2) tag rules."""
from __future__ import annotations
from dota_core.roast.tag_rules import safe_get

_T = {
    "mid_lane_lost_score":    38,    # early_position_score below
    "mid_lane_lost_deaths":   4,     # deaths in early phase proxy
    "no_rotation_kpm":        0.13,  # (kills+assists)/min below — not rotating
    "no_rotation_mid_score":  45,
    "tempo_vacuum_score":     42,
    "tempo_vacuum_assists":   5,     # low assists by 35 min
    "fed_enemy_early_score":  38,
    "fed_enemy_deaths":       4,
    "low_damage_dpm":         320,   # hero_damage/min — mid should deal more
    "mid_no_scaling_mid":     44,    # mid_score below
    "mid_no_scaling_late":    44,    # late_score below
    "mid_died_solo_ratio":    0.4,   # kills/(kills+deaths) below — dying more than killing
    "mid_died_solo_deaths":   5,
    "passive_mid_kpm":        0.10,
    "passive_mid_dpm":        300,
}


def tag_mid(player: dict, match_context: dict) -> list[str]:
    tags: list[str] = []

    early_score = safe_get(player, "early_position_score")
    mid_score   = safe_get(player, "mid_position_score")
    late_score  = safe_get(player, "late_position_score")
    kills       = safe_get(player, "kills", 0)
    assists     = safe_get(player, "assists", 0)
    deaths      = safe_get(player, "deaths", 0)
    hero_dmg    = safe_get(player, "hero_damage")
    duration    = safe_get(player, "duration_min", 1.0)

    # mid_lane_lost
    if early_score is not None and early_score < _T["mid_lane_lost_score"]:
        tags.append("mid_lane_lost")
    elif deaths is not None and deaths >= _T["mid_lane_lost_deaths"] and early_score is not None and early_score < 45:
        tags.append("mid_lane_lost")

    # no_rotation_mid: low k+a rate + bad mid phase score
    if duration > 0 and kills is not None and assists is not None:
        kpm = (kills + assists) / duration
        if kpm < _T["no_rotation_kpm"] and (mid_score is None or mid_score < _T["no_rotation_mid_score"]):
            tags.append("no_rotation_mid")

    # tempo_vacuum: weak mid phase + low assists
    if mid_score is not None and mid_score < _T["tempo_vacuum_score"]:
        if assists is not None and assists < _T["tempo_vacuum_assists"]:
            tags.append("tempo_vacuum")

    # mid_fed_enemy
    if early_score is not None and deaths is not None:
        if early_score < _T["fed_enemy_early_score"] and deaths >= _T["fed_enemy_deaths"]:
            tags.append("mid_fed_enemy")

    # low_damage_mid
    if hero_dmg is not None and duration > 0:
        if (hero_dmg / duration) < _T["low_damage_dpm"]:
            tags.append("low_damage_mid")

    # mid_no_scaling: bad mid AND bad late
    if mid_score is not None and late_score is not None:
        if mid_score < _T["mid_no_scaling_mid"] and late_score < _T["mid_no_scaling_late"]:
            tags.append("mid_no_scaling")

    # mid_died_solo: high death, low kill ratio
    if kills is not None and deaths is not None and deaths >= _T["mid_died_solo_deaths"]:
        ratio = kills / max(kills + deaths, 1)
        if ratio < _T["mid_died_solo_ratio"]:
            tags.append("mid_died_solo")

    # passive_mid: very low participation + low damage
    if duration > 0 and kills is not None and assists is not None and hero_dmg is not None:
        kpm = (kills + assists) / duration
        dpm = hero_dmg / duration
        if kpm < _T["passive_mid_kpm"] and dpm < _T["passive_mid_dpm"]:
            tags.append("passive_mid")

    return tags
