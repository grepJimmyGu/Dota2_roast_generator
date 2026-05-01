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

_CARRY_MID = {"carry", "mid"}
_SUPPORT   = {"pos4", "pos5"}

# Chinese display names for role keys used throughout the roast pipeline
ROLE_NAMES_ZH: dict[str, str] = {
    "carry":   "核心（一号位）",
    "mid":     "中单（二号位）",
    "offlane": "上路（三号位）",
    "pos4":    "游走辅助（四号位）",
    "pos5":    "硬辅（五号位）",
}

RESULT_ZH = {"win": "胜", "loss": "负", "unknown": "未知"}


def _translate_role_keys(d: dict) -> dict:
    """Replace English role keys with Chinese in a dict."""
    return {ROLE_NAMES_ZH.get(k, k): v for k, v in d.items()}


def _select_critique_focus(primary_role: str, role_distribution: dict[str, int], total: int) -> str:
    dominant = None
    for role, count in role_distribution.items():
        if count / total >= 0.5:
            dominant = role
            break

    if dominant is None:
        return "跨角色分析：玩家在多个位置之间频繁切换，缺乏稳定性。重点关注跨角色共性问题。"

    role_zh = ROLE_NAMES_ZH.get(dominant, dominant)
    if dominant in _CARRY_MID:
        return f"主位 {role_zh}：重点分析资源转化效率、推进节奏、输出与推塔贡献。"
    if dominant == "offlane":
        return f"主位 {role_zh}：重点分析开团质量、制造空间、承伤效率和推塔影响力。"
    if dominant in _SUPPORT:
        return f"主位 {role_zh}：重点分析视野控制、死亡次数、保人贡献和团战参与度。"

    return f"主位 {role_zh}：综合分析近10场表现。"


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
                "标签":     tag.label_zh,
                "吐槽角度": tag.roast_angle,
                "严重程度": tag.severity_score,
            })

    # Translate evidence role/result fields to Chinese
    evidence_zh: dict = {}
    for key, val in evidence.items():
        if val is None:
            continue
        entry = dict(val)
        entry["role"]   = ROLE_NAMES_ZH.get(entry.get("role", ""), entry.get("role", ""))
        entry["result"] = RESULT_ZH.get(entry.get("result", ""), entry.get("result", ""))
        evidence_zh[key] = entry

    return {
        "玩家名称":       (player_profile or {}).get("playerName") or "该玩家",
        "总场次":         total,
        "主要位置":       ROLE_NAMES_ZH.get(primary_role, primary_role),
        "位置分布":       _translate_role_keys(role_distribution),
        "位置数据":       {ROLE_NAMES_ZH.get(k, k): v for k, v in role_patterns.items()},
        "分析重点":       critique_focus,
        "基调":           tone,
        "总体统计": {
            k: v for k, v in overall_summary.items()
            if v is not None and v != [] and v != {}
        },
        "反复出现的问题标签": enriched_tags,
        "典型场次证据":       evidence_zh,
    }
