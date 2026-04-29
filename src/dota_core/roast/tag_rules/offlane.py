"""Offlane (Pos 3) tag rules."""
from __future__ import annotations
from dota_core.roast.tag_rules import safe_get

_T = {
    "no_initiation_kpm":      0.10,  # (kills+assists)/min below
    "no_initiation_score":    44,
    "paper_ofl_deaths_pm":    0.22,
    "paper_ofl_score":        44,
    "no_space_score":         44,
    "no_space_tower_dmg":     1800,
    "fed_carry_early_score":  38,
    "fed_carry_deaths":       4,
    "no_dmg_no_tank_dmg_pm":  250,   # hero_damage/min
    "no_dmg_no_tank_score":   40,
    "suicide_ratio":          0.35,  # kills/(kills+deaths) — dying without killing
    "suicide_deaths":         6,
    "lost_lane_score":        35,
    "lost_lane_deaths":       5,
}


def tag_offlane(player: dict, match_context: dict) -> list[str]:
    tags: list[str] = []

    early_score = safe_get(player, "early_position_score")
    mid_score   = safe_get(player, "mid_position_score")
    kills       = safe_get(player, "kills", 0)
    assists     = safe_get(player, "assists", 0)
    deaths      = safe_get(player, "deaths", 0)
    hero_dmg    = safe_get(player, "hero_damage")
    tower_dmg   = safe_get(player, "tower_damage")
    score       = safe_get(player, "overall_score")
    duration    = safe_get(player, "duration_min", 1.0)

    # no_initiation: low participation + weak mid score
    if duration > 0 and kills is not None and assists is not None:
        kpm = (kills + assists) / duration
        if kpm < _T["no_initiation_kpm"] and (mid_score is None or mid_score < _T["no_initiation_score"]):
            tags.append("no_initiation")

    # paper_offlaner: high deaths + low overall score
    if deaths is not None and duration > 0 and score is not None:
        dpm = deaths / duration
        if (dpm >= _T["paper_ofl_deaths_pm"] or deaths >= 8) and score < _T["paper_ofl_score"]:
            tags.append("paper_offlaner")

    # no_space_created: low score + low tower damage + low assists
    if score is not None and score < _T["no_space_score"]:
        if tower_dmg is not None and tower_dmg < _T["no_space_tower_dmg"]:
            tags.append("no_space_created")

    # fed_enemy_carry: bad early phase + deaths
    if early_score is not None and deaths is not None:
        if early_score < _T["fed_carry_early_score"] and deaths >= _T["fed_carry_deaths"]:
            tags.append("fed_enemy_carry")

    # offlane_no_damage_no_tank: low damage AND low score
    if hero_dmg is not None and score is not None and duration > 0:
        dpm = hero_dmg / duration
        if dpm < _T["no_dmg_no_tank_dmg_pm"] and score < _T["no_dmg_no_tank_score"]:
            tags.append("offlane_no_damage_no_tank")

    # suicide_initiator: dying a lot without killing
    if kills is not None and deaths is not None and deaths >= _T["suicide_deaths"]:
        ratio = kills / max(kills + deaths, 1)
        if ratio < _T["suicide_ratio"]:
            tags.append("suicide_initiator")

    # lost_hard_lane: very bad early score + deaths
    if early_score is not None and early_score < _T["lost_lane_score"]:
        tags.append("lost_hard_lane")
    elif early_score is not None and deaths is not None:
        if early_score < 42 and deaths >= _T["lost_lane_deaths"]:
            tags.append("lost_hard_lane")

    return tags
