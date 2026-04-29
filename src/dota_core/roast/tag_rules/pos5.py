"""Hard Support (Pos 5) tag rules."""
from __future__ import annotations
from dota_core.roast.tag_rules import safe_get

_T = {
    "feed_deaths":          8,
    "feed_deaths_pm":       0.22,
    "greedy_gpm":           280,    # pos5 above this is suspect
    "greedy_assists_pm":    0.10,
    "no_lane_early_score":  38,
    "no_lane_assists":      3,
    "no_impact_score":      38,
    "no_impact_assists":    5,
    "no_impact_kills":      2,
}


def tag_pos5(player: dict, match_context: dict) -> list[str]:
    tags: list[str] = []

    kills       = safe_get(player, "kills", 0)
    assists     = safe_get(player, "assists", 0)
    deaths      = safe_get(player, "deaths", 0)
    gpm         = safe_get(player, "gold_per_min")
    score       = safe_get(player, "overall_score")
    early_score = safe_get(player, "early_position_score")
    duration    = safe_get(player, "duration_min", 1.0)

    # pos5_feed: high deaths
    if deaths is not None and duration > 0:
        dpm = deaths / duration
        if deaths >= _T["feed_deaths"] or dpm >= _T["feed_deaths_pm"]:
            tags.append("pos5_feed")

    # greedy_pos5: high GPM for a hard support + low assist rate
    if gpm is not None and gpm >= _T["greedy_gpm"] and duration > 0:
        if assists is not None and (assists / duration) < _T["greedy_assists_pm"]:
            tags.append("greedy_pos5")

    # no_lane_protection: bad early score + low assists
    if early_score is not None and early_score < _T["no_lane_early_score"]:
        if assists is not None and assists < _T["no_lane_assists"]:
            tags.append("no_lane_protection")

    # pos5_no_impact: bad score + low kills + low assists
    if score is not None and score < _T["no_impact_score"]:
        if (assists is not None and assists < _T["no_impact_assists"]
                and kills is not None and kills < _T["no_impact_kills"]):
            tags.append("pos5_no_impact")

    return tags
