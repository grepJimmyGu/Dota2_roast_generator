"""
Assemble all analysis into a single LLM-ready context dict.

Maps to spec: packages/core/roast/longform_context_builder.py
"""
from __future__ import annotations
from collections import Counter
from dota_core.roast.models import PlayerMatchStats
from dota_core.roast.multi_match_summary import summarize_last_matches, ROLE_NAMES
from dota_core.roast.role_pattern_summary import summarize_role_patterns
from dota_core.roast.evidence_selector import select_critique_evidence
from dota_core.roast.roast_tags import ROAST_TAG_REGISTRY

_CARRY_MID   = {"carry", "mid"}
_SUPPORT     = {"pos4", "pos5"}


def _select_critique_focus(primary_role: str, role_distribution: dict[str, int], total: int) -> str:
    """
    Determine the critique angle based on role dominance.

    Rules (from spec):
    - If one role >= 50% → focus on that role
    - No dominant role → cross-role habits
    - carry/mid dominant → resource conversion, tempo, damage, objectives
    - support dominant → vision, death control, saves, teamfight utility
    - offlane dominant → initiation, space creation, tanking, objectives
    """
    dominant = None
    for role, count in role_distribution.items():
        if count / total >= 0.5:
            dominant = role
            break

    if dominant is None:
        return "跨角色分析：玩家在多个位置之间频繁切换，缺乏稳定性。重点关注跨角色共性问题。"

    if dominant in _CARRY_MID:
        return f"主位 {dominant}：重点分析资源转化效率、推进节奏、输出与推塔贡献。"
    if dominant == "offlane":
        return "主位 offlane：重点分析开团质量、制造空间、承伤效率和推塔影响力。"
    if dominant in _SUPPORT:
        return f"主位 {dominant}：重点分析视野控制、死亡次数、保人贡献和团战参与度。"

    return f"主位 {dominant}：综合分析近10场表现。"


def build_longform_critique_context(
    matches: list[PlayerMatchStats],
    player_profile: dict | None = None,
) -> dict:
    """
    Build a fully-structured context dict for the LLM prompt.

    player_profile: optional dict with {playerName, steamId, rank}
    """
    overall_summary = summarize_last_matches(matches)
    role_patterns   = summarize_role_patterns(matches)
    evidence        = select_critique_evidence(matches)

    primary_role       = overall_summary.get("primary_role", "unknown")
    role_distribution  = overall_summary.get("role_distribution", {})
    total              = overall_summary.get("total_matches", len(matches))
    critique_focus     = _select_critique_focus(primary_role, role_distribution, total or 1)

    # Tone: scale based on severity
    high_sev = overall_summary.get("high_severity_match_count", 0)
    if high_sev >= 6:
        tone = "high"
    elif high_sev >= 3:
        tone = "medium"
    else:
        tone = "light"

    # Build enriched roast tag list: top recurring tags with label + roast angle
    raw_tag_ids = overall_summary.get("most_common_problem_tags", [])
    enriched_tags = []
    for tag_id in raw_tag_ids:
        tag = ROAST_TAG_REGISTRY.get(tag_id)
        if tag:
            enriched_tags.append({
                "tag_id":      tag.tag_id,
                "label_zh":    tag.label_zh,
                "roast_angle": tag.roast_angle,
                "severity":    tag.severity_score,
            })

    return {
        "player_name":            (player_profile or {}).get("playerName") or "该玩家",
        "steam_id":               (player_profile or {}).get("steamId"),
        "total_matches":          total,
        "overall_summary":        overall_summary,
        "role_distribution":      role_distribution,
        "primary_role":           primary_role,
        "role_patterns":          role_patterns,
        "recurring_roast_tags":   enriched_tags,
        "selected_evidence":      evidence,
        "critique_focus":         critique_focus,
        "tone_level":             tone,
    }
