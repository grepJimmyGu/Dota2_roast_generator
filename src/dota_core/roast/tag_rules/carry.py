"""Carry (Pos 1) tag rules."""
from __future__ import annotations
from dota_core.roast.tag_rules import safe_get

_T = {
    "farm_black_hole_gpm":       520,    # high GPM but...
    "farm_black_hole_dmg_ratio": 0.60,   # hero_damage / (net_worth * 0.8) below this
    "afk_farmer_assists_pm":     0.08,   # assists/min below this
    "afk_farmer_lh_min":         180,    # last_hits above this (farming a lot)
    "paper_carry_deaths_pm":     0.20,   # deaths/min
    "paper_carry_deaths_abs":    7,
    "late_no_impact_score":      42,     # late_position_score below
    "late_no_impact_min_dur":    35,     # only flag in long games
    "carry_no_obj_dmg":          2000,
    "low_dmg_high_farm_gpm":     480,    # gpm high...
    "low_dmg_high_farm_dpm":     280,    # ...but hero_damage/min low
    "useless_six_slot_dur":      55,     # very long game
    "useless_six_slot_score":    45,
    "lane_disaster_early_score": 35,
    "lane_disaster_lh":          100,    # very low last hits for a carry
    "fed_ofl_early_score":       38,
    "fed_ofl_deaths":            4,
}


def tag_carry(player: dict, match_context: dict) -> list[str]:
    tags: list[str] = []

    gpm         = safe_get(player, "gold_per_min")
    net_worth   = safe_get(player, "net_worth")
    hero_dmg    = safe_get(player, "hero_damage")
    tower_dmg   = safe_get(player, "tower_damage")
    assists     = safe_get(player, "assists", 0)
    kills       = safe_get(player, "kills", 0)
    deaths      = safe_get(player, "deaths", 0)
    last_hits   = safe_get(player, "last_hits")
    duration    = safe_get(player, "duration_min", 1.0)
    early_score = safe_get(player, "early_position_score")
    late_score  = safe_get(player, "late_position_score")
    score       = safe_get(player, "overall_score")

    # farm_black_hole: high GPM but very low damage/tower relative to farm
    if gpm and net_worth and hero_dmg:
        dmg_ratio = hero_dmg / max(net_worth * 0.8, 1)
        if gpm >= _T["farm_black_hole_gpm"] and dmg_ratio < _T["farm_black_hole_dmg_ratio"]:
            tags.append("farm_black_hole")

    # afk_farmer: high last hits but low assist participation
    if assists is not None and duration > 0 and last_hits is not None:
        apm = (assists + kills) / duration
        if last_hits >= _T["afk_farmer_lh_min"] and apm < _T["afk_farmer_assists_pm"]:
            tags.append("afk_farmer")

    # paper_carry: high deaths for a carry
    if deaths is not None and duration > 0:
        dpm = deaths / duration
        if dpm >= _T["paper_carry_deaths_pm"] or deaths >= _T["paper_carry_deaths_abs"]:
            tags.append("paper_carry")

    # late_no_impact: long game + bad late score
    if late_score is not None and duration >= _T["late_no_impact_min_dur"]:
        if late_score < _T["late_no_impact_score"]:
            tags.append("late_no_impact")

    # carry_no_objective: low tower damage
    if tower_dmg is not None and tower_dmg < _T["carry_no_obj_dmg"]:
        tags.append("carry_no_objective")

    # low_damage_high_farm: good GPM, weak damage output
    if gpm and hero_dmg and duration > 0:
        dpm = hero_dmg / duration
        if gpm >= _T["low_dmg_high_farm_gpm"] and dpm < _T["low_dmg_high_farm_dpm"]:
            tags.append("low_damage_high_farm")

    # useless_six_slot: very long game + still low score
    if duration >= _T["useless_six_slot_dur"] and score is not None:
        if score < _T["useless_six_slot_score"]:
            tags.append("useless_six_slot")

    # carry_lane_disaster: terrible early phase
    if early_score is not None and early_score < _T["lane_disaster_early_score"]:
        tags.append("carry_lane_disaster")
    elif last_hits is not None and last_hits < _T["lane_disaster_lh"] and duration > 25:
        tags.append("carry_lane_disaster")

    # carry_fed_offlane: bad early + died a lot early
    if early_score is not None and deaths is not None:
        if early_score < _T["fed_ofl_early_score"] and deaths >= _T["fed_ofl_deaths"]:
            tags.append("carry_fed_offlane")

    return tags
