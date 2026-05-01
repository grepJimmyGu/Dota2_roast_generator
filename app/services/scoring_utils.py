"""
Shared scoring utilities used by both player_service and match_service.
"""
from __future__ import annotations
import math
import statistics
from collections import Counter, defaultdict

# Human-readable labels for per-stat z-score keys
STAT_LABELS: dict[str, str] = {
    "net_worth_gain":   "Net Worth",
    "damage_dealt":     "Hero Damage",
    "healing":          "Healing",
    "tower_damage":     "Tower Damage",
    "last_hits":        "Last Hits",
    "denies":           "Denies",
    "kills_in_phase":   "Kills",
    "assists_in_phase": "Assists",
    "vacancy_time":     "Lane Presence",
    "aggression":       "Aggression",
}

PHASE_LABELS = {
    "early_game": "lane phase",
    "mid_game":   "mid game",
    "late_game":  "closing",
}


def derive_strengths_weaknesses(
    stat_breakdown: dict[str, dict[str, float]],
) -> tuple[list[str] | None, list[str] | None]:
    """
    Aggregate per-stat signed z-scores across all phases and return top-3 strengths
    and bottom-3 weaknesses as human-readable label lists.

    stat_breakdown: {phase: {stat_key: signed_zscore}}
    Positive z = performed well; negative z = fell short (signs already corrected by score_breakdown).
    """
    if not stat_breakdown:
        return None, None

    totals: dict[str, list[float]] = defaultdict(list)
    for phase_scores in stat_breakdown.values():
        for stat, z in phase_scores.items():
            totals[stat].append(z)

    avg_z = {stat: sum(zs) / len(zs) for stat, zs in totals.items()}
    ranked = sorted(avg_z.items(), key=lambda x: x[1], reverse=True)

    # Threshold: |z| > 0.4 — suppress near-average stats from appearing as strengths/weaknesses.
    # z=0.4 ≈ top 34th percentile; below this the signal is too noisy to surface to users.
    THRESHOLD = 0.4
    strengths  = [STAT_LABELS.get(s, s) for s, z in ranked        if z >  THRESHOLD][:3] or None
    weaknesses = [STAT_LABELS.get(s, s) for s, z in reversed(ranked) if z < -THRESHOLD][:3] or None
    return strengths, weaknesses


def derive_phase_labels(
    early: float | None,
    mid: float | None,
    late: float | None,
) -> tuple[str | None, str | None]:
    """
    Given position scores for the three phases, return (strongest_phase, weakest_phase)
    as human-readable labels. Returns None for any phase that lacks a score.
    """
    scores = {
        "early_game": early,
        "mid_game":   mid,
        "late_game":  late,
    }
    available = {k: v for k, v in scores.items() if v is not None}
    if not available:
        return None, None

    strongest_key = max(available, key=lambda k: available[k])
    weakest_key   = min(available, key=lambda k: available[k])

    # Only label weakest if there's meaningful separation
    strongest = PHASE_LABELS[strongest_key]
    weakest   = PHASE_LABELS[weakest_key] if weakest_key != strongest_key else None
    return strongest, weakest


def generate_match_summary(
    strongest_phase: str | None,
    weakest_phase: str | None,
    strengths: list[str] | None,
    weaknesses: list[str] | None,
    overall_position_score: float | None,
    is_partial: bool,
    scored_stat_count: int = 0,
) -> str | None:
    """
    Produce a one-sentence plain-English summary of a match.
    Rules-based: no ML, no external calls.

    scored_stat_count: number of stats that contributed to the score — used to
    soften language when benchmark coverage is thin (< 3 stats).
    """
    if is_partial or overall_position_score is None:
        return "Scoring data incomplete for this match."

    # Soften summary when very few stats were scored (thin benchmark coverage)
    if scored_stat_count < 3:
        return "Limited benchmark data — score may not fully reflect performance."

    score = overall_position_score
    top_strength  = strengths[0]  if strengths  else None
    top_weakness  = weaknesses[0] if weaknesses else None

    # Score band
    if score >= 65:
        opener = "Strong overall performance"
    elif score >= 50:
        opener = "Solid role execution"
    elif score >= 35:
        opener = "Mixed performance"
    else:
        opener = "Struggled against role benchmarks"

    # Phase contrast
    if strongest_phase and weakest_phase and strongest_phase != weakest_phase:
        phase_clause = f"best in {strongest_phase}, with room to improve in {weakest_phase}"
    elif strongest_phase:
        phase_clause = f"most impactful in {strongest_phase}"
    else:
        phase_clause = None

    # Stat flavour
    if top_strength and top_weakness:
        stat_clause = f"stood out on {top_strength}, but fell short on {top_weakness}"
    elif top_strength:
        stat_clause = f"excelled on {top_strength}"
    elif top_weakness:
        stat_clause = f"fell short on {top_weakness}"
    else:
        stat_clause = None

    parts = [opener]
    if phase_clause:
        parts.append(phase_clause)
    if stat_clause:
        parts.append(stat_clause)

    return " — ".join(parts) + "."


# ---------------------------------------------------------------------------
# UI v1 — richer content generation
# ---------------------------------------------------------------------------

PHASE_DISPLAY = {
    "early_game": "lane phase",
    "mid_game":   "mid game",
    "late_game":  "closing phase",
}

PHASE_DISPLAY_ZH = {
    "early_game": "对线阶段",
    "mid_game":   "中期",
    "late_game":  "后期",
}

POSITION_ARCHETYPE: dict[int, str] = {
    1: "Farming Core",
    2: "Tempo Mid",
    3: "Space Creator",
    4: "Playmaker",
    5: "Vision Support",
}

POSITION_ARCHETYPE_ZH: dict[int, str] = {
    1: "农场核心",
    2: "节奏中路",
    3: "空间制造者",
    4: "打手辅助",
    5: "视野辅助",
}

STAT_LABELS_ZH: dict[str, str] = {
    "net_worth_gain":   "净资产",
    "damage_dealt":     "英雄伤害",
    "healing":          "治疗量",
    "tower_damage":     "建筑伤害",
    "last_hits":        "补刀",
    "denies":           "反补",
    "kills_in_phase":   "击杀",
    "assists_in_phase": "助攻",
    "vacancy_time":     "道路存在感",
    "aggression":       "攻击性",
    "deaths_in_phase":  "死亡次数",
}

_IMPROVEMENT_RULES: list[tuple] = [
    (1, "late_game",  "Tower Damage",  "Convert late-game farm into building pressure — push towers after winning fights."),
    (1, "mid_game",   "Tower Damage",  "Turn midgame gold leads into towers — avoid sitting on farm without objective follow-up."),
    (1, None,         "Lane Presence", "Reduce idle farming minutes — stay active between waves to maintain map presence."),
    (1, None,         "Hero Damage",   "Transition resource leads into fights — your farm needs to translate into damage output."),
    (2, "mid_game",   "Tower Damage",  "Prioritize T1 pressure after winning lane — midgame rotations should target buildings."),
    (2, "mid_game",   None,            "Improve midgame map influence — rotations, kills, and tower dives all drive tempo."),
    (2, None,         "Hero Damage",   "Find more active fight windows — tempo mids need to deal damage to generate leads."),
    (3, "mid_game",   "Aggression",    "Increase midgame harassment pressure — sustained offlane aggression disrupts enemy farm patterns."),
    (3, "mid_game",   None,            "Focus on midgame space creation — opening the map is the core offlane responsibility."),
    (3, None,         "Tower Damage",  "Turn survivability into objective pressure — space creation means threatening buildings."),
    (4, "mid_game",   None,            "Prioritize midgame rotations — playmaker impact comes from timely ganks and vision setups."),
    (4, None,         "Assists",       "Look for more fight participation — assists are the primary playmaker contribution metric."),
    (5, "late_game",  None,            "Stay active on the map in late game — vision and positioning decide team fights at this stage."),
    (5, None,         "Tower Damage",  "Focus on vision control over damage numbers — ward placement is your primary objective contribution."),
]


def get_performance_archetype(position: int, lang: str = "en") -> str | None:
    if lang == "zh":
        return POSITION_ARCHETYPE_ZH.get(position)
    return POSITION_ARCHETYPE.get(position)


def generate_match_narrative(
    strongest_phase: str | None,
    weakest_phase: str | None,
    strengths: list[str] | None,
    weaknesses: list[str] | None,
    overall_position_score: float | None,
    overall_hero_score: float | None,
    position: int,
    is_partial: bool,
    scored_stat_count: int = 0,
    lang: str = "en",
) -> str | None:
    if is_partial or overall_position_score is None:
        return None
    if scored_stat_count < 3:
        return "Limited benchmark data available for this match." if lang == "en" else "基准数据不足，无法生成完整分析。"

    archetype = get_performance_archetype(position, lang)
    score     = overall_position_score
    top_s     = strengths[0]  if strengths  else None
    top_w     = weaknesses[0] if weaknesses else None

    if lang == "zh":
        if score >= 65:
            opening = f"作为{archetype}，这是一场出色的表现。" if archetype else "这场比赛整体表现出色。"
        elif score >= 50:
            opening = f"作为{archetype}，这场比赛发挥较为稳定。" if archetype else "本场位置发挥较为稳定。"
        elif score >= 35:
            opening = f"{archetype}位置的发挥参差不齐。" if archetype else "本场表现有得有失。"
        else:
            opening = f"作为{archetype}，本场发挥未能达到位置基准。" if archetype else "本场表现未能达到位置基准。"

        phase_sentence = None
        if strongest_phase and weakest_phase and strongest_phase != weakest_phase:
            phase_sentence = f"{strongest_phase}阶段影响力最强，{weakest_phase}阶段有所下滑。"
        elif strongest_phase:
            phase_sentence = f"{strongest_phase}是表现最突出的阶段。"

        contrast = None
        if overall_hero_score is not None:
            gap = overall_position_score - overall_hero_score
            if gap >= 10:
                contrast = "位置基准表现优于英雄专项基准，本场更多体现了位置职责的执行。"
            elif gap <= -10:
                contrast = "英雄专项执行是更强的信号——位置层面的贡献相对滞后。"

        signal = None
        if top_s and top_w:
            signal = f"{top_s}是本场最大亮点，{top_w}是主要拖累。"
        elif top_s:
            signal = f"{top_s}是本场最突出的正向贡献。"
        elif top_w:
            signal = f"{top_w}是本场表现的主要拖累项。"

        return "".join(p for p in [opening, phase_sentence, contrast, signal] if p)

    if score >= 65:
        opening = f"A strong performance in the {archetype} role." if archetype else "A strong overall performance."
    elif score >= 50:
        opening = f"A solid showing as a {archetype}." if archetype else "A solid role performance."
    elif score >= 35:
        opening = f"A mixed game in the {archetype} role." if archetype else "A mixed performance against role benchmarks."
    else:
        opening = f"A difficult game in the {archetype} role." if archetype else "Performance fell short of role benchmarks."

    phase_sentence = None
    if strongest_phase and weakest_phase and strongest_phase != weakest_phase:
        phase_sentence = f"Impact was highest in {strongest_phase} and dipped in {weakest_phase}."
    elif strongest_phase:
        phase_sentence = f"{strongest_phase.capitalize()} was the strongest phase."

    contrast = None
    if overall_hero_score is not None:
        gap = overall_position_score - overall_hero_score
        if gap >= 10:
            contrast = "Role execution outpaced hero-specific benchmarks — performance was positionally driven."
        elif gap <= -10:
            contrast = "Hero-specific execution was the stronger signal — role-level contribution lagged."

    signal = None
    if top_s and top_w:
        signal = f"{top_s} was the standout positive; {top_w} was the main drag."
    elif top_s:
        signal = f"{top_s} was the standout contribution."
    elif top_w:
        signal = f"{top_w} was the primary drag on this performance."

    return " ".join(p for p in [opening, phase_sentence, contrast, signal] if p)


def generate_phase_narrative(
    phase: str,
    position_score: float | None,
    stat_breakdown: dict[str, float],
    lang: str = "en",
) -> str | None:
    if position_score is None:
        return None

    top_pos = max(
        ((s, z) for s, z in stat_breakdown.items() if z > 0.4 and STAT_LABELS.get(s)),
        key=lambda x: x[1], default=None,
    )
    top_neg = min(
        ((s, z) for s, z in stat_breakdown.items() if z < -0.4 and STAT_LABELS.get(s)),
        key=lambda x: x[1], default=None,
    )

    if lang == "zh":
        if position_score >= 65:   assessment = "位置表现出色"
        elif position_score >= 50: assessment = "高于平均水平"
        elif position_score >= 35: assessment = "低于平均水平"
        else:                      assessment = "本阶段表现较弱"
        s_label = STAT_LABELS_ZH.get(top_pos[0]) if top_pos else None
        w_label = STAT_LABELS_ZH.get(top_neg[0]) if top_neg else None
        if s_label and w_label:
            return f"{assessment} — {s_label}是主要亮点，{w_label}是主要拖累。"
        elif s_label:
            return f"{assessment} — {s_label}推动表现超越基准。"
        elif w_label:
            return f"{assessment} — {w_label}拖累了本阶段表现。"
        return f"{assessment} — 本阶段无显著信号。"

    if position_score >= 65:   assessment = "Strong role execution"
    elif position_score >= 50: assessment = "Above average"
    elif position_score >= 35: assessment = "Below average"
    else:                      assessment = "Weak phase"

    if top_pos and top_neg:
        return f"{assessment} — {STAT_LABELS[top_pos[0]]} was the key strength, {STAT_LABELS[top_neg[0]]} the main drag."
    elif top_pos:
        return f"{assessment} — {STAT_LABELS[top_pos[0]]} drove performance above benchmark."
    elif top_neg:
        return f"{assessment} — {STAT_LABELS[top_neg[0]]} pulled performance below benchmark."
    return f"{assessment} — no dominant signal in this phase."


def generate_biggest_edge(
    strengths: list[str] | None,
    strongest_phase: str | None,
    stat_breakdown: dict[str, dict[str, float]],
    lang: str = "en",
) -> str | None:
    if not strengths:
        return None
    top_en = strengths[0]
    top    = STAT_LABELS_ZH.get(next((k for k, v in STAT_LABELS.items() if v == top_en), ""), top_en) if lang == "zh" else top_en
    key    = next((k for k, v in STAT_LABELS.items() if v == top_en), None)
    strong_phases = [PHASE_DISPLAY.get(p, p) for p, ps in stat_breakdown.items() if key and ps.get(key, 0) > 0.4]

    if lang == "zh":
        if strong_phases:
            phases_str = "和".join(strong_phases[:2])
            return f"{top} — 在{phases_str}阶段持续超越基准，是本场最稳定的正向信号。"
        elif strongest_phase:
            return f"{top} — 最可靠的正向指标，在{strongest_phase}阶段尤为突出。"
        return f"{top} — 本场最稳定的正向贡献项。"

    if strong_phases:
        return f"{top_en} — consistently above benchmark, particularly in {' and '.join(strong_phases[:2])}."
    elif strongest_phase:
        return f"{top_en} — your most reliable positive signal, especially in {strongest_phase}."
    return f"{top_en} — the most consistent positive contribution this match."


def generate_biggest_liability(
    weaknesses: list[str] | None,
    weakest_phase: str | None,
    lang: str = "en",
) -> str | None:
    if not weaknesses:
        return None
    top_en = weaknesses[0]
    top    = STAT_LABELS_ZH.get(next((k for k, v in STAT_LABELS.items() if v == top_en), ""), top_en) if lang == "zh" else top_en
    if lang == "zh":
        if weakest_phase:
            return f"{top} — 本场最大的拖累项，在{weakest_phase}阶段最为明显。"
        return f"{top} — 在各阶段持续低于位置基准。"
    if weakest_phase:
        return f"{top_en} — the biggest drag on performance, most pronounced in {weakest_phase}."
    return f"{top_en} — consistently below role benchmark across phases."


_IMPROVEMENT_RULES_ZH: list[tuple] = [
    (1, "late_game",  "Tower Damage",  "将后期农场优势转化为推塔压力 — 赢得团战后立即拆塔。"),
    (1, "mid_game",   "Tower Damage",  "将中期金币优势兑换为建筑 — 避免只刷钱不推进。"),
    (1, None,         "Lane Presence", "减少闲置时间 — 保持在关键区域的活跃存在。"),
    (1, None,         "Hero Damage",   "将资源优势转化为团战输出 — 农场需要兑现为伤害。"),
    (2, "mid_game",   "Tower Damage",  "中路赢得对线后优先拆一塔 — 中期游走应以拆塔为目标。"),
    (2, "mid_game",   None,            "提升中期地图影响力 — 游走、击杀和拆塔都是节奏来源。"),
    (2, None,         "Hero Damage",   "寻找更多主动出击的机会 — 节奏中路需要通过输出产生影响。"),
    (3, "mid_game",   "Aggression",    "加强中期骚扰压力 — 持续骚扰是三路制造空间的核心方式。"),
    (3, "mid_game",   None,            "专注中期空间制造 — 开放地图是三号位的核心职责。"),
    (3, None,         "Tower Damage",  "将生存优势转化为推塔压力 — 制造空间意味着威胁建筑。"),
    (4, "mid_game",   None,            "优先中期游走 — 打手辅助的影响力来自及时的gank和视野配置。"),
    (4, None,         "Assists",       "寻找更多参团机会 — 助攻是打手辅助的核心贡献指标。"),
    (5, "late_game",  None,            "后期保持地图活跃 — 视野和站位决定后期团战胜负。"),
    (5, None,         "Tower Damage",  "专注视野控制而非伤害数据 — 插眼是五号位的核心目标贡献。"),
]


def generate_improvement_suggestion(
    weakest_phase: str | None,
    weaknesses: list[str] | None,
    position: int,
    lang: str = "en",
) -> str | None:
    top_w = weaknesses[0] if weaknesses else None
    rules = _IMPROVEMENT_RULES_ZH if lang == "zh" else _IMPROVEMENT_RULES
    for rule_pos, rule_phase, rule_weakness, suggestion in rules:
        if (rule_pos   is None or rule_pos   == position) and \
           (rule_phase is None or rule_phase == weakest_phase) and \
           (rule_weakness is None or (top_w and rule_weakness in top_w)):
            return suggestion

    if lang == "zh":
        if weakest_phase == "early_game": return "强化对线阶段基本功 — 早期基准差距会在后续持续累积。"
        if weakest_phase == "mid_game":   return "提升中期地图活跃度 — 13-40分钟的团战和目标都需要关注。"
        if weakest_phase == "late_game":  return "提升后期关闭能力 — 后期团战和推塔是决定比赛的关键。"
        if top_w:
            top_zh = STAT_LABELS_ZH.get(next((k for k, v in STAT_LABELS.items() if v == top_w), ""), top_w)
            return f"重点改善{top_zh} — 这是你最持续低于基准的领域。"
        return None

    if weakest_phase == "early_game": return "Strengthen lane phase fundamentals — early benchmark gaps compound later."
    if weakest_phase == "mid_game":   return "Improve midgame map activity — fights and objectives both need attention between 13–40 min."
    if weakest_phase == "late_game":  return "Improve closing-phase contribution — late fights and towers decide most games."
    if top_w:
        return f"Work on {top_w} — it's your most persistent below-benchmark area."
    return None


def compute_consistency_rating(scores: list[float]) -> str | None:
    clean = [s for s in scores if s is not None]
    if len(clean) < 4:
        return None
    try:
        stddev = statistics.stdev(clean)
    except statistics.StatisticsError:
        return None
    if stddev < 8:
        return "Consistent"
    if stddev < 15:
        return "Variable"
    return "Volatile"


def compute_recurring_patterns(
    score_rows,
    threshold: int = 3,
) -> tuple[list[str] | None, list[str] | None]:
    s_counter: Counter = Counter()
    w_counter: Counter = Counter()
    for row in score_rows:
        for label in (row.top_strengths  or []):
            s_counter[label] += 1
        for label in (row.top_weaknesses or []):
            w_counter[label] += 1
    recurring_s = [l for l, c in s_counter.most_common() if c >= threshold][:3] or None
    recurring_w = [l for l, c in w_counter.most_common() if c >= threshold][:3] or None
    return recurring_s, recurring_w


def generate_player_narrative(
    archetype: str | None,
    strongest_phase: str | None,
    weakest_phase: str | None,
    recurring_strengths: list[str] | None,
    recurring_weaknesses: list[str] | None,
    consistency_rating: str | None,
    recent_trend: str | None,
    average_overall_score: float | None,
    match_count: int,
    lang: str = "en",
) -> str | None:
    if match_count < 3:
        return "Not enough recent matches to build a reliable profile." if lang == "en" else "近期比赛场次不足，暂无可靠的表现分析。"
    if average_overall_score is None:
        return None

    score = average_overall_score

    if lang == "zh":
        if archetype:
            if score >= 60:   opening = f"近期主打{archetype}，整体表现较强。"
            elif score >= 45: opening = f"近期{archetype}位置发挥参差不齐。"
            else:             opening = f"近期{archetype}位置表现持续低于基准。"
        else:
            opening = "近期整体表现偏弱。" if score < 60 else "近期整体表现较为稳定。"

        phase_sentence = None
        if strongest_phase and weakest_phase and strongest_phase != weakest_phase:
            phase_sentence = f"{strongest_phase}是最稳定的强势阶段，{weakest_phase}是最需要改进的方向。"
        elif strongest_phase:
            phase_sentence = f"{strongest_phase}是最可靠的表现阶段。"

        pattern_sentence = None
        rs = recurring_strengths[0] if recurring_strengths else None
        rw = recurring_weaknesses[0] if recurring_weaknesses else None
        if rs and rw:
            pattern_sentence = f"{rs}是持续出现的优势项；{rw}是持续存在的薄弱环节。"
        elif rs:
            pattern_sentence = f"{rs}是近期比赛中可靠的重复优势。"
        elif rw:
            pattern_sentence = f"{rw}在近期多场比赛中持续出现为薄弱点。"

        consistency_sentence = None
        if consistency_rating == "Consistent" and recent_trend == "improving":
            consistency_sentence = "评分稳定且呈上升趋势。"
        elif consistency_rating == "Volatile":
            consistency_sentence = "表现波动较大 — 强场和弱场同时出现。"
        elif consistency_rating == "Variable":
            consistency_sentence = "近期比赛表现差异较明显。"
        elif consistency_rating == "Consistent":
            consistency_sentence = "场与场之间的评分较为一致。"

        return "".join(p for p in [opening, phase_sentence, pattern_sentence, consistency_sentence] if p)

    if archetype:
        if score >= 60:   opening = f"Playing primarily as a {archetype}, recent form has been strong."
        elif score >= 45: opening = f"In the {archetype} role, performance has been mixed recently."
        else:             opening = f"{archetype} games have been below role benchmarks lately."
    else:
        opening = "Recent form has been mixed." if score < 60 else "Recent form has been strong."

    phase_sentence = None
    if strongest_phase and weakest_phase and strongest_phase != weakest_phase:
        phase_sentence = f"{strongest_phase.capitalize()} is consistently the strongest phase; {weakest_phase} remains the main area to develop."
    elif strongest_phase:
        phase_sentence = f"{strongest_phase.capitalize()} is the most reliable phase."

    pattern_sentence = None
    if recurring_strengths and recurring_weaknesses:
        pattern_sentence = f"{recurring_strengths[0]} is a recurring strength; {recurring_weaknesses[0]} is a persistent weak area."
    elif recurring_strengths:
        pattern_sentence = f"{recurring_strengths[0]} appears as a reliable recurring strength."
    elif recurring_weaknesses:
        pattern_sentence = f"{recurring_weaknesses[0]} is a persistent weak area across recent matches."

    consistency_sentence = None
    if consistency_rating == "Consistent" and recent_trend == "improving":
        consistency_sentence = "Scores have been consistent and trending upward."
    elif consistency_rating == "Volatile":
        consistency_sentence = "Results have been volatile — strong and poor games are both appearing."
    elif consistency_rating == "Variable":
        consistency_sentence = "Performance has varied notably across recent matches."
    elif consistency_rating == "Consistent":
        consistency_sentence = "Scores have been consistent match to match."

    return " ".join(p for p in [opening, phase_sentence, pattern_sentence, consistency_sentence] if p)


def generate_player_summary(
    strongest_phase: str | None,
    weakest_phase: str | None,
    recent_trend: str | None,
    average_overall_score: float | None,
    match_count: int,
) -> str | None:
    """
    Produce a one-sentence plain-English summary across a player's recent matches.
    """
    if match_count == 0:
        return "No recent ranked matches found."

    if average_overall_score is None:
        return "Not enough scored matches to summarize performance yet."

    score = average_overall_score

    if score >= 65:
        level = "consistently strong role execution"
    elif score >= 50:
        level = "solid role execution"
    elif score >= 35:
        level = "mixed role execution"
    else:
        level = "room for improvement across roles"

    phase_clause = None
    if strongest_phase and weakest_phase and strongest_phase != weakest_phase:
        phase_clause = f"strongest in {strongest_phase}, with {weakest_phase} as the main improvement area"
    elif strongest_phase:
        phase_clause = f"most consistent in {strongest_phase}"

    trend_clause = None
    if recent_trend == "improving":
        trend_clause = "recent trend is improving"
    elif recent_trend == "declining":
        trend_clause = "recent trend is declining"

    parts = [level.capitalize()]
    if phase_clause:
        parts.append(phase_clause)
    if trend_clause:
        parts.append(trend_clause)

    return " — ".join(parts) + "."


# ---------------------------------------------------------------------------
# UI v2 — score distribution context
# ---------------------------------------------------------------------------

# Score follows approximately N(50, 16.67) since score = (z + 3) / 6 * 100
# and z ~ N(0, 1). The normal approximation is a reasonable proxy for MVP;
# true distributions vary slightly by position, hero, and stat coverage.
# TODO: replace with empirically sampled distributions when score history is sufficient.
_SCORE_MU    = 50.0
_SCORE_SIGMA = 100.0 / 6.0   # ≈ 16.67


def compute_score_percentile(score: float) -> float:
    """Return the approximate percentile (0–100) for a score using normal CDF."""
    z = (score - _SCORE_MU) / (_SCORE_SIGMA * math.sqrt(2))
    return round((1.0 + math.erf(z)) / 2.0 * 100, 1)


_BRACKET_LABELS: dict[str, str] = {
    "HERALD_GUARDIAN":  "Herald / Guardian",
    "CRUSADER_ARCHON":  "Crusader / Archon",
    "LEGEND_ANCIENT":   "Legend / Ancient",
    "DIVINE_IMMORTAL":  "Divine / Immortal",
}

_BRACKET_LABELS_ZH: dict[str, str] = {
    "HERALD_GUARDIAN":  "先驱 / 卫士",
    "CRUSADER_ARCHON":  "圣堂 / 执政",
    "LEGEND_ANCIENT":   "传说 / 远古",
    "DIVINE_IMMORTAL":  "天神 / 不朽",
}

def _percentile_label(percentile: float, lang: str = "en") -> str:
    if lang == "zh":
        if percentile >= 90: return "前10%"
        if percentile >= 80: return "前20%"
        if percentile >= 70: return "前30%"
        if percentile >= 60: return "高于平均"
        if percentile >= 40: return "接近平均"
        if percentile >= 20: return "低于平均"
        return "后20%"
    if percentile >= 90: return "Top 10%"
    if percentile >= 80: return "Top 20%"
    if percentile >= 70: return "Top 30%"
    if percentile >= 60: return "Above average"
    if percentile >= 40: return "Around average"
    if percentile >= 20: return "Below average"
    return "Bottom 20%"


def build_score_context(score: float, bracket: str | None = None, lang: str = "en") -> dict:
    """Return a ScoreContextSchema-compatible dict for a score value."""
    percentile   = compute_score_percentile(score)
    bracket_labels = _BRACKET_LABELS_ZH if lang == "zh" else _BRACKET_LABELS
    return {
        "score":        round(score, 1),
        "benchmarkAvg": _SCORE_MU,
        "percentile":   percentile,
        "label":        _percentile_label(percentile, lang),
        "bracket":      bracket,
        "bracketLabel": bracket_labels.get(bracket) if bracket else None,
    }


# ---------------------------------------------------------------------------
# UI v2 — deeper match analysis entries
# ---------------------------------------------------------------------------

# Implication phrases per stat, direction
_STAT_IMPLICATION: dict[str, dict[str, str]] = {
    "net_worth_gain": {
        "positive": "building a resource advantage ahead of role benchmarks",
        "negative": "falling behind on the resource curve expected for this role",
    },
    "damage_dealt": {
        "positive": "contributing above-benchmark fight output and pressure",
        "negative": "below-benchmark hero damage reduced fight and carry impact",
    },
    "tower_damage": {
        "positive": "converting advantages into objective and map pressure",
        "negative": "failing to translate advantages into tower and map control",
    },
    "last_hits": {
        "positive": "maintaining strong CS efficiency and income parity",
        "negative": "falling behind on CS — a key income metric for this role",
    },
    "kills_in_phase": {
        "positive": "generating kill pressure and tempo for the team",
        "negative": "limited kill contribution where active pressure was expected",
    },
    "assists_in_phase": {
        "positive": "high fight participation and consistent teamwork contribution",
        "negative": "low fight participation — a key metric for this role",
    },
    "vacancy_time": {
        "positive": "minimal idle time — staying active and productive on the map",
        "negative": "extended idle periods reduced effective farm and map presence",
    },
    "aggression": {
        "positive": "sustained harassment pressure maintained fight tempo",
        "negative": "limited harassment reduced the offlane's space-creation impact",
    },
    "deaths_in_phase": {
        "positive": "strong survival kept momentum and resource flow intact",
        "negative": "repeated deaths disrupted tempo and created resource gaps for the enemy",
    },
}

_STAT_IMPLICATION_ZH: dict[str, dict[str, str]] = {
    "net_worth_gain": {
        "positive": "净资产超越了位置基准，建立了资源优势",
        "negative": "净资产落后于该位置应有水平，资源差距需要弥补",
    },
    "damage_dealt": {
        "positive": "英雄伤害高于基准，团战输出贡献突出",
        "negative": "英雄伤害低于基准，团战输出存在明显差距",
    },
    "tower_damage": {
        "positive": "推塔和目标伤害超越基准，有效转化了优势",
        "negative": "推塔伤害明显不足，优势未能转化为地图控制",
    },
    "last_hits": {
        "positive": "补刀效率高于基准，收入节奏稳定",
        "negative": "补刀数落后，资源收入不足是主要问题",
    },
    "kills_in_phase": {
        "positive": "击杀压制有效，为队伍创造了节奏优势",
        "negative": "击杀参与不足，未能形成应有的压制效果",
    },
    "assists_in_phase": {
        "positive": "参团率高，团队协作贡献突出",
        "negative": "参团率偏低，该位置应有更高的助攻贡献",
    },
    "vacancy_time": {
        "positive": "闲置时间少，地图存在感和运营效率较高",
        "negative": "闲置时间过长，有效农场和地图存在感受到影响",
    },
    "aggression": {
        "positive": "持续的骚扰压制维持了三路节奏",
        "negative": "骚扰力度不足，制造空间的核心职责未能充分发挥",
    },
    "deaths_in_phase": {
        "positive": "存活意识强，保持了己方的节奏和资源优势",
        "negative": "多次死亡打断了节奏，并为对方提供了资源差距",
    },
}

_STAT_WHY_MATTERS_ZH: dict[str, str] = {
    "net_worth_gain":   "经济效率直接决定关键装备的成型时间。",
    "damage_dealt":     "英雄伤害是衡量团战贡献的核心指标。",
    "tower_damage":     "推塔是个人表现转化为团队胜利的关键途径。",
    "last_hits":        "补刀数决定资源收入和全局装备节奏。",
    "kills_in_phase":   "击杀压制能制造金币差和时间窗口优势。",
    "assists_in_phase": "高助攻率代表有效的团战参与和协作能力。",
    "vacancy_time":     "保持地图存在感才能最大化每分钟效率。",
    "aggression":       "上路骚扰压制直接影响己方核心的发育空间。",
    "deaths_in_phase":  "死亡次数影响金币损失和团战可用性。",
}

_STAT_WHY_MATTERS: dict[str, str] = {
    "net_worth_gain":   "Farm efficiency directly determines power spikes and item timing.",
    "damage_dealt":     "Hero damage is the primary indicator of fight impact.",
    "tower_damage":     "Objective pressure is how individual performance converts into team wins.",
    "last_hits":        "CS rate determines resource income and item timing throughout the game.",
    "kills_in_phase":   "Kill pressure creates gold leads and timing windows for the team.",
    "assists_in_phase": "High assist rate indicates effective teamfight participation.",
    "vacancy_time":     "Active map presence maximizes efficiency and reduces wasted potential.",
    "aggression":       "Offlane harassment determines how much space the core can farm.",
    "deaths_in_phase":  "Death count impacts both gold loss and team fight availability.",
}

# Map stat_key → phaseStats camelCase key (for concrete value lookup)
_STAT_TO_PHASE_KEY: dict[str, str] = {
    "net_worth_gain":   "netWorth",
    "damage_dealt":     "heroDamage",
    "tower_damage":     "towerDamage",
    "last_hits":        "lastHits",
    "kills_in_phase":   "kills",
    "deaths_in_phase":  "deaths",
}


def _z_magnitude(z: float, positive: bool) -> str:
    az = abs(z)
    if az > 1.5:
        return "significantly above benchmark" if positive else "significantly below benchmark"
    if az > 0.8:
        return "clearly above benchmark" if positive else "clearly below benchmark"
    return "above benchmark" if positive else "below benchmark"


def _make_went_well_entry(phase: str, stat: str, z: float, phase_stats: dict | None, lang: str = "en") -> dict:
    label_en    = STAT_LABELS.get(stat, stat)
    label       = STAT_LABELS_ZH.get(stat, label_en) if lang == "zh" else label_en
    phase_label = (PHASE_DISPLAY_ZH if lang == "zh" else PHASE_DISPLAY).get(phase, phase)
    magnitude   = _z_magnitude(z, True)
    impl_map    = _STAT_IMPLICATION_ZH if lang == "zh" else _STAT_IMPLICATION
    why_map     = _STAT_WHY_MATTERS_ZH if lang == "zh" else _STAT_WHY_MATTERS
    implication = impl_map.get(stat, {}).get("positive", "outperforming the role benchmark" if lang == "en" else "超越位置基准")
    why         = why_map.get(stat, "This metric reflects role effectiveness." if lang == "en" else "该指标反映位置执行效率。")

    val_key = _STAT_TO_PHASE_KEY.get(stat)
    val     = (phase_stats or {}).get(phase, {}).get(val_key) if val_key else None
    val_str = f"（{val:,}）" if val and lang == "zh" else (f" ({val:,})" if val else "")

    if lang == "zh":
        mag_zh = {"significantly above benchmark": "显著超越基准", "clearly above benchmark": "明显超越基准", "above benchmark": "高于基准"}.get(magnitude, magnitude)
        detail = f"本场{phase_label}阶段{label}{val_str}{mag_zh} — {implication}。这是本阶段相对于位置和段位基准最明显的正向信号之一。"
        takeaway = f"这是你的可靠优势 — 继续在{phase_label}阶段保持{label}的高水平。"
        return {"title": f"{label}优势", "detail": detail, "phase": phase_label, "whyItMatters": why, "takeaway": takeaway}

    detail = (f"Your {label}{val_str} in {phase_label} was {magnitude} — {implication}. "
              f"This was one of the clearer positive signals in this phase relative to your role and bracket.")
    takeaway = f"This is a reliable strength — continue prioritising {label_en.lower()} in {phase_label}."
    return {"title": f"Strong {label_en}", "detail": detail, "phase": phase_label, "whyItMatters": why, "takeaway": takeaway}


def _make_hurt_most_entry(phase: str, stat: str, z: float, phase_stats: dict | None, lang: str = "en") -> dict:
    label_en    = STAT_LABELS.get(stat, stat)
    label       = STAT_LABELS_ZH.get(stat, label_en) if lang == "zh" else label_en
    phase_label = (PHASE_DISPLAY_ZH if lang == "zh" else PHASE_DISPLAY).get(phase, phase)
    magnitude   = _z_magnitude(z, False)
    impl_map    = _STAT_IMPLICATION_ZH if lang == "zh" else _STAT_IMPLICATION
    why_map     = _STAT_WHY_MATTERS_ZH if lang == "zh" else _STAT_WHY_MATTERS
    implication = impl_map.get(stat, {}).get("negative", "falling short of the role benchmark" if lang == "en" else "低于位置基准")
    why         = why_map.get(stat, "This metric reflects role effectiveness." if lang == "en" else "该指标反映位置执行效率。")

    val_key = _STAT_TO_PHASE_KEY.get(stat)
    val     = (phase_stats or {}).get(phase, {}).get(val_key) if val_key else None
    val_str = f"（{val:,}）" if val and lang == "zh" else (f" ({val:,})" if val else "")

    if lang == "zh":
        mag_zh = {"significantly below benchmark": "显著低于基准", "clearly below benchmark": "明显低于基准", "below benchmark": "低于基准"}.get(magnitude, magnitude)
        detail = f"本场{phase_label}阶段{label}{val_str}{mag_zh} — {implication}。这是本阶段相对于位置基准最明显的负向信号之一。"
        takeaway = f"重点关注{phase_label}阶段的{label} — 这是本场最需要改进的差距。"
        return {"title": f"{label}不足", "detail": detail, "phase": phase_label, "whyItMatters": why, "takeaway": takeaway}

    detail = (f"Your {label_en}{val_str} in {phase_label} was {magnitude} — {implication}. "
              f"This was one of the clearest drags on performance relative to your role benchmark in this phase.")
    takeaway = f"Address {label_en.lower()} in {phase_label} — it's your most consistent gap in this area."
    return {"title": f"Weak {label_en}", "detail": detail, "phase": phase_label, "whyItMatters": why, "takeaway": takeaway}


def _make_work_on_entry(phase: str, stat: str, z: float, position: int,
                         weakest_phase: str | None, lang: str = "en") -> dict:
    label_en    = STAT_LABELS.get(stat, stat)
    label       = STAT_LABELS_ZH.get(stat, label_en) if lang == "zh" else label_en
    phase_label = (PHASE_DISPLAY_ZH if lang == "zh" else PHASE_DISPLAY).get(phase, phase)
    why_map     = _STAT_WHY_MATTERS_ZH if lang == "zh" else _STAT_WHY_MATTERS
    why         = why_map.get(stat, "This metric reflects role effectiveness." if lang == "en" else "该指标反映位置执行效率。")
    suggestion  = generate_improvement_suggestion(weakest_phase, [label_en], position, lang)

    if lang == "zh":
        mag_zh = {"significantly below benchmark": "显著低于基准", "clearly below benchmark": "明显低于基准", "below benchmark": "低于基准"}.get(_z_magnitude(z, False), "低于基准")
        detail = f"本场最值得优先改进的是{phase_label}阶段的{label}，{mag_zh}。{suggestion or f'重点关注{phase_label}阶段的{label}提升。'}"
        takeaway = suggestion or f"优先改进{phase_label}阶段的{label}。"
        return {"title": f"改进{label}", "detail": detail, "phase": phase_label, "whyItMatters": why, "takeaway": takeaway}

    suggestion_en = generate_improvement_suggestion(weakest_phase, [label_en], position, "en")
    detail = (f"Your highest-leverage improvement in this game is {label_en.lower()} in {phase_label}, "
              f"which fell {_z_magnitude(z, False)}. {suggestion_en or ''}")
    return {"title": f"Improve {label_en}", "detail": detail, "phase": phase_label,
            "whyItMatters": why, "takeaway": suggestion_en or f"Focus on {label_en.lower()} in {phase_label}."}


def generate_match_analysis(
    stat_breakdown: dict[str, dict[str, float]],
    phase_stats: dict | None,
    position: int,
    overall_position_score: float | None,
    weakest_phase: str | None,
    is_partial: bool,
    scored_stat_count: int = 0,
    lang: str = "en",
) -> dict | None:
    """
    Generate richer match analysis buckets: wentWell, hurtMost, workOn.
    Returns a MatchAnalysisSchema-compatible dict, or None if data is thin.
    """
    if is_partial or not stat_breakdown or scored_stat_count < 3:
        return None

    best_per_stat: dict[str, tuple[str, float]] = {}
    for phase, stats in stat_breakdown.items():
        for stat, z in stats.items():
            if stat not in best_per_stat or abs(z) > abs(best_per_stat[stat][1]):
                best_per_stat[stat] = (phase, z)

    positives = sorted(
        [(stat, phase, z) for stat, (phase, z) in best_per_stat.items() if z > 0.4],
        key=lambda x: x[2], reverse=True,
    )
    negatives = sorted(
        [(stat, phase, z) for stat, (phase, z) in best_per_stat.items() if z < -0.4],
        key=lambda x: x[2],
    )

    went_well = [_make_went_well_entry(phase, stat, z, phase_stats, lang) for stat, phase, z in positives[:3]]
    hurt_most = [_make_hurt_most_entry(phase, stat, z, phase_stats, lang) for stat, phase, z in negatives[:3]]
    work_on   = [_make_work_on_entry(phase, stat, z, position, weakest_phase, lang) for stat, phase, z in negatives[:2]]

    return {"wentWell": went_well, "hurtMost": hurt_most, "workOn": work_on}


# ---------------------------------------------------------------------------
# UI v2 — enriched recurring patterns with win/loss evidence
# ---------------------------------------------------------------------------

def _pattern_summary(label: str, frequency: int, total: int, is_strength: bool, lang: str = "en") -> str:
    pct = round(frequency / max(total, 1) * 100)
    if frequency >= max(total * 0.7, 3): consistency = ("consistently", "持续")
    elif frequency >= max(total * 0.5, 3): consistency = ("frequently", "频繁")
    else: consistency = ("repeatedly", "多次")

    if lang == "zh":
        if is_strength:
            return (f"你{consistency[1]}展现出高于基准的{label} — 在近{total}场中的{frequency}场（{pct}%）中被识别为优势项。"
                    f"这是你较为可靠的正向表现规律之一。")
        else:
            return (f"{label}在近{total}场中的{frequency}场（{pct}%）中持续出现为薄弱项。"
                    f"这是一个跨英雄和比赛状态都存在的结构性差距。")

    direction = "strength" if is_strength else "weakness"
    if is_strength:
        return (f"You {consistency[0]} show above-benchmark {label} — it appeared as a strength "
                f"in {frequency} of your last {total} matches ({pct}%). "
                f"This is one of your more reliable positive patterns.")
    else:
        return (f"{label} appeared as a persistent {direction} in {frequency} of your last "
                f"{total} matches ({pct}%). "
                f"This is a recurring gap that shows up across different heroes and game states.")


def _win_loss_interpretation(label: str, is_strength: bool,
                              has_wins: bool, has_losses: bool, lang: str = "en") -> str | None:
    if not has_wins or not has_losses:
        return None
    if lang == "zh":
        if is_strength:
            return (f"在胜场中，{label}优势往往配合了更好的整体影响力转化。"
                    f"在败场中，这一优势依然存在，但不足以弥补其他方面的差距 — 说明它是稳定的正向因素，但并非决定性因素。")
        else:
            return (f"在{label}被标记的败场中，差距更为明显，可能直接影响了比赛结果。"
                    f"即便在部分胜场中这一领域也表现欠佳，证明这是持续性的结构问题而非偶发性失误。")
    if is_strength:
        return (f"In winning games, this {label} strength often combined with better overall impact "
                f"conversion. In losses, the edge was still present but wasn't enough to overcome "
                f"other deficits — suggesting it's a consistent positive but not a deciding factor alone.")
    else:
        return (f"In losses where {label} was flagged, the gap was more pronounced and likely "
                f"contributed to the result. Even in some wins this area underperformed, "
                f"confirming it as a persistent structural weakness rather than a situational one.")


def generate_recurring_pattern_entries(
    match_records: list[dict],
    threshold: int = 3,
    lang: str = "en",
) -> list[dict]:
    """
    Build enriched recurring pattern entries from per-match records.

    match_records: list of dicts with keys:
      match_id, hero_name, won, overall_score, strengths (list[str]), weaknesses (list[str])

    Returns list of RecurringPatternEntrySchema-compatible dicts.
    """
    if not match_records:
        return []

    total = len(match_records)
    s_counter: Counter = Counter()
    w_counter: Counter = Counter()

    for r in match_records:
        for label in (r.get("strengths") or []):
            s_counter[label] += 1
        for label in (r.get("weaknesses") or []):
            w_counter[label] += 1

    entries: list[dict] = []

    def _make_entry(label: str, frequency: int, is_strength: bool) -> dict:
        counter_key = "strengths" if is_strength else "weaknesses"
        relevant = [r for r in match_records if label in (r.get(counter_key) or [])]
        wins   = [r for r in relevant if r.get("won") is True]
        losses = [r for r in relevant if r.get("won") is False]

        win_ex = max(wins,   key=lambda r: r.get("overall_score") or 0, default=None)
        loss_ex= max(losses, key=lambda r: -(r.get("overall_score") or 100), default=None)

        def _ex(r):
            if not r:
                return None
            return {
                "matchId":      r["match_id"],
                "heroName":     r.get("hero_name"),
                "result":       "win" if r.get("won") else "loss",
                "overallScore": r.get("overall_score"),
            }

        why_map = _STAT_WHY_MATTERS_ZH if lang == "zh" else _STAT_WHY_MATTERS
        stat_key = next((k for k, v in STAT_LABELS.items() if v == label), None)
        why = why_map.get(stat_key, ("该指标反映位置执行效率。" if lang == "zh" else "This metric reflects role effectiveness."))

        return {
            "label":                 label,
            "frequency":             frequency,
            "totalMatches":          total,
            "isStrength":            is_strength,
            "summary":               _pattern_summary(label, frequency, total, is_strength, lang),
            "whyItMatters":          why,
            "winExample":            _ex(win_ex),
            "lossExample":           _ex(loss_ex),
            "winLossInterpretation": _win_loss_interpretation(label, is_strength, bool(wins), bool(losses), lang),
        }

    for label, count in s_counter.most_common(3):
        if count >= threshold:
            entries.append(_make_entry(label, count, is_strength=True))

    for label, count in w_counter.most_common(3):
        if count >= threshold:
            entries.append(_make_entry(label, count, is_strength=False))

    return entries
