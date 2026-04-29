"""Soft Support (Pos 4) tag rules."""
from __future__ import annotations
from dota_core.roast.tag_rules import safe_get

_T = {
    "no_roam_kpm":         0.11,   # (kills+assists)/min below
    "no_roam_mid_score":   44,
    "greedy_gpm":          330,    # pos4 above this is suspect
    "greedy_assists_pm":   0.12,
    "no_impact_score":     40,
    "no_impact_assists":   6,      # assists total
    "feed_deaths":         7,
    "feed_kill_ratio":     0.35,   # kills/(kills+deaths)
    "bad_lane_early":      38,
    "bad_lane_assists":    3,
    "dmg_padding_dpm":     280,    # decent damage...
    "dmg_padding_score":   46,     # ...but low overall impact
    "dmg_padding_assists": 6,
}


def tag_pos4(player: dict, match_context: dict) -> list[str]:
    tags: list[str] = []

    kills       = safe_get(player, "kills", 0)
    assists     = safe_get(player, "assists", 0)
    deaths      = safe_get(player, "deaths", 0)
    gpm         = safe_get(player, "gold_per_min")
    hero_dmg    = safe_get(player, "hero_damage")
    score       = safe_get(player, "overall_score")
    early_score = safe_get(player, "early_position_score")
    mid_score   = safe_get(player, "mid_position_score")
    duration    = safe_get(player, "duration_min", 1.0)

    # pos4_no_roam: low k+a rate + bad mid phase
    if duration > 0 and kills is not None and assists is not None:
        kpm = (kills + assists) / duration
        if kpm < _T["no_roam_kpm"] and (mid_score is None or mid_score < _T["no_roam_mid_score"]):
            tags.append("pos4_no_roam")

    # pos4_greedy: high GPM for a support + low assists rate
    if gpm is not None and gpm >= _T["greedy_gpm"] and duration > 0:
        if assists is not None and (assists / duration) < _T["greedy_assists_pm"]:
            tags.append("pos4_greedy")

    # pos4_no_impact: very low score + low assists
    if score is not None and score < _T["no_impact_score"]:
        if assists is not None and assists < _T["no_impact_assists"]:
            tags.append("pos4_no_impact")

    # pos4_feed: high deaths + low kill payoff
    if deaths is not None and deaths >= _T["feed_deaths"] and kills is not None:
        ratio = kills / max(kills + deaths, 1)
        if ratio < _T["feed_kill_ratio"]:
            tags.append("pos4_feed")

    # pos4_bad_lane: bad early score + minimal assist contribution
    if early_score is not None and early_score < _T["bad_lane_early"]:
        if assists is not None and assists < _T["bad_lane_assists"]:
            tags.append("pos4_bad_lane")

    # pos4_damage_padding: dealing damage but not contributing to team
    if hero_dmg is not None and score is not None and duration > 0:
        dpm = hero_dmg / duration
        if dpm >= _T["dmg_padding_dpm"] and score < _T["dmg_padding_score"]:
            if assists is not None and assists < _T["dmg_padding_assists"]:
                tags.append("pos4_damage_padding")

    return tags
