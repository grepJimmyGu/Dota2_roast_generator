"""
Tag engine — given a player dict and position, run the appropriate rule
functions and return a deduplicated list of tag_ids sorted by severity.

Maps to spec: the tagging step that feeds into longform_context_builder.
"""
from __future__ import annotations
from dota_core.roast.roast_tags import ROAST_TAG_REGISTRY
from dota_core.roast.tag_rules.common   import tag_common
from dota_core.roast.tag_rules.carry    import tag_carry
from dota_core.roast.tag_rules.mid      import tag_mid
from dota_core.roast.tag_rules.offlane  import tag_offlane
from dota_core.roast.tag_rules.pos4     import tag_pos4
from dota_core.roast.tag_rules.pos5     import tag_pos5

_ROLE_RULES = {
    1: tag_carry,
    2: tag_mid,
    3: tag_offlane,
    4: tag_pos4,
    5: tag_pos5,
}


def run_tag_rules(player: dict, match_context: dict | None = None) -> list[str]:
    """
    Run common + role-specific rules for the player's position.
    Returns deduplicated tag_ids sorted by severity (highest first).
    Never raises — missing data is handled inside each rule function.
    """
    ctx = match_context or player
    position = player.get("position", 0)

    tag_ids: set[str] = set(tag_common(player, ctx))

    role_fn = _ROLE_RULES.get(position)
    if role_fn:
        tag_ids.update(role_fn(player, ctx))

    # Sort by severity descending
    return sorted(
        tag_ids,
        key=lambda tid: ROAST_TAG_REGISTRY.get(tid, type("", (), {"severity_score": 0})()).severity_score,
        reverse=True,
    )


def player_stats_to_dict(m) -> dict:
    """
    Convert a PlayerMatchStats instance to the flat dict expected by tag rules.
    Also works if m is already a dict.
    """
    if isinstance(m, dict):
        return m
    return {
        "match_id":             m.match_id,
        "hero_id":              m.hero_id,
        "hero_name":            m.hero_name,
        "position":             m.position,
        "won":                  m.won,
        "duration_min":         m.duration_min,
        "kills":                m.kills,
        "deaths":               m.deaths,
        "assists":              m.assists,
        "overall_score":        m.overall_score,
        "position_score":       m.position_score,
        "hero_score":           m.hero_score,
        "early_position_score": m.early_position_score,
        "mid_position_score":   m.mid_position_score,
        "late_position_score":  m.late_position_score,
        "weaknesses":           m.weaknesses,
        "strengths":            m.strengths,
        "hero_damage":          m.hero_damage,
        "tower_damage":         m.tower_damage,
        "net_worth":            m.net_worth,
        "gold_per_min":         m.gold_per_min,
        "last_hits":            m.last_hits,
    }
