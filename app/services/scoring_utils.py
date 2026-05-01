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

POSITION_ARCHETYPE: dict[int, str] = {
    1: "Farming Core",
    2: "Tempo Mid",
    3: "Space Creator",
    4: "Playmaker",
    5: "Vision Support",
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


def get_performance_archetype(position: int) -> str | None:
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
) -> str | None:
    if is_partial or overall_position_score is None:
        return None
    if scored_stat_count < 3:
        return "Limited benchmark data available for this match."

    archetype = get_performance_archetype(position)
    score     = overall_position_score
    top_s     = strengths[0]  if strengths  else None
    top_w     = weaknesses[0] if weaknesses else None

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
) -> str | None:
    if position_score is None:
        return None

    if position_score >= 65:
        assessment = "Strong role execution"
    elif position_score >= 50:
        assessment = "Above average"
    elif position_score >= 35:
        assessment = "Below average"
    else:
        assessment = "Weak phase"

    top_pos = max(
        ((s, z) for s, z in stat_breakdown.items() if z > 0.4 and STAT_LABELS.get(s)),
        key=lambda x: x[1], default=None,
    )
    top_neg = min(
        ((s, z) for s, z in stat_breakdown.items() if z < -0.4 and STAT_LABELS.get(s)),
        key=lambda x: x[1], default=None,
    )

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
) -> str | None:
    if not strengths:
        return None
    top = strengths[0]
    key = next((k for k, v in STAT_LABELS.items() if v == top), None)
    strong_phases = [
        PHASE_DISPLAY.get(phase, phase)
        for phase, ps in stat_breakdown.items()
        if key and ps.get(key, 0) > 0.4
    ]
    if strong_phases:
        return f"{top} — consistently above benchmark, particularly in {' and '.join(strong_phases[:2])}."
    elif strongest_phase:
        return f"{top} — your most reliable positive signal, especially in {strongest_phase}."
    return f"{top} — the most consistent positive contribution this match."


def generate_biggest_liability(
    weaknesses: list[str] | None,
    weakest_phase: str | None,
) -> str | None:
    if not weaknesses:
        return None
    top = weaknesses[0]
    if weakest_phase:
        return f"{top} — the biggest drag on performance, most pronounced in {weakest_phase}."
    return f"{top} — consistently below role benchmark across phases."


def generate_improvement_suggestion(
    weakest_phase: str | None,
    weaknesses: list[str] | None,
    position: int,
) -> str | None:
    top_w = weaknesses[0] if weaknesses else None
    for rule_pos, rule_phase, rule_weakness, suggestion in _IMPROVEMENT_RULES:
        if (rule_pos   is None or rule_pos   == position) and \
           (rule_phase is None or rule_phase == weakest_phase) and \
           (rule_weakness is None or (top_w and rule_weakness in top_w)):
            return suggestion
    if weakest_phase == "early_game":
        return "Strengthen lane phase fundamentals — early benchmark gaps compound later."
    if weakest_phase == "mid_game":
        return "Improve midgame map activity — fights and objectives both need attention between 13–40 min."
    if weakest_phase == "late_game":
        return "Improve closing-phase contribution — late fights and towers decide most games."
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
) -> str | None:
    if match_count < 3:
        return "Not enough recent matches to build a reliable profile."
    if average_overall_score is None:
        return None

    score = average_overall_score

    if archetype:
        if score >= 60:
            opening = f"Playing primarily as a {archetype}, recent form has been strong."
        elif score >= 45:
            opening = f"In the {archetype} role, performance has been mixed recently."
        else:
            opening = f"{archetype} games have been below role benchmarks lately."
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


def _percentile_label(percentile: float) -> str:
    if percentile >= 90: return "Top 10%"
    if percentile >= 80: return "Top 20%"
    if percentile >= 70: return "Top 30%"
    if percentile >= 60: return "Above average"
    if percentile >= 40: return "Around average"
    if percentile >= 20: return "Below average"
    return "Bottom 20%"


def build_score_context(score: float) -> dict:
    """Return a ScoreContextSchema-compatible dict for a score value."""
    percentile = compute_score_percentile(score)
    return {
        "score":        round(score, 1),
        "benchmarkAvg": _SCORE_MU,
        "percentile":   percentile,
        "label":        _percentile_label(percentile),
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


def _make_went_well_entry(phase: str, stat: str, z: float, phase_stats: dict | None) -> dict:
    label        = STAT_LABELS.get(stat, stat)
    phase_label  = PHASE_DISPLAY.get(phase, phase)
    magnitude    = _z_magnitude(z, True)
    implication  = _STAT_IMPLICATION.get(stat, {}).get("positive", "outperforming the role benchmark")
    why          = _STAT_WHY_MATTERS.get(stat, "This metric reflects role effectiveness.")

    # Pull concrete value if available
    val_key  = _STAT_TO_PHASE_KEY.get(stat)
    val      = (phase_stats or {}).get(phase, {}).get(val_key) if val_key else None
    val_str  = f" ({val:,})" if val else ""

    detail = (
        f"Your {label}{val_str} in {phase_label} was {magnitude} — {implication}. "
        f"This was one of the clearer positive signals in this phase relative to your role and bracket."
    )
    takeaway = f"This is a reliable strength — continue prioritising {label.lower()} in {phase_label}."

    return {"title": f"Strong {label}", "detail": detail, "phase": phase_label,
            "whyItMatters": why, "takeaway": takeaway}


def _make_hurt_most_entry(phase: str, stat: str, z: float, phase_stats: dict | None) -> dict:
    label       = STAT_LABELS.get(stat, stat)
    phase_label = PHASE_DISPLAY.get(phase, phase)
    magnitude   = _z_magnitude(z, False)
    implication = _STAT_IMPLICATION.get(stat, {}).get("negative", "falling short of the role benchmark")
    why         = _STAT_WHY_MATTERS.get(stat, "This metric reflects role effectiveness.")

    val_key = _STAT_TO_PHASE_KEY.get(stat)
    val     = (phase_stats or {}).get(phase, {}).get(val_key) if val_key else None
    val_str = f" ({val:,})" if val else ""

    detail = (
        f"Your {label}{val_str} in {phase_label} was {magnitude} — {implication}. "
        f"This was one of the clearest drags on performance relative to your role benchmark in this phase."
    )
    takeaway = f"Address {label.lower()} in {phase_label} — it's your most consistent gap in this area."

    return {"title": f"Weak {label}", "detail": detail, "phase": phase_label,
            "whyItMatters": why, "takeaway": takeaway}


def _make_work_on_entry(phase: str, stat: str, z: float, position: int,
                         weakest_phase: str | None) -> dict:
    label       = STAT_LABELS.get(stat, stat)
    phase_label = PHASE_DISPLAY.get(phase, phase)
    suggestion  = generate_improvement_suggestion(weakest_phase, [label], position) or (
        f"Focus on {label.lower()} in {phase_label} — this is the highest-leverage gap in this game."
    )
    why = _STAT_WHY_MATTERS.get(stat, "This metric reflects role effectiveness.")

    detail = (
        f"Your highest-leverage improvement in this game is {label.lower()} in {phase_label}, "
        f"which fell {_z_magnitude(z, False)}. "
        f"{suggestion}"
    )

    return {"title": f"Improve {label}", "detail": detail, "phase": phase_label,
            "whyItMatters": why, "takeaway": suggestion}


def generate_match_analysis(
    stat_breakdown: dict[str, dict[str, float]],
    phase_stats: dict | None,
    position: int,
    overall_position_score: float | None,
    weakest_phase: str | None,
    is_partial: bool,
    scored_stat_count: int = 0,
) -> dict | None:
    """
    Generate richer match analysis buckets: wentWell, hurtMost, workOn.
    Returns a MatchAnalysisSchema-compatible dict, or None if data is thin.
    """
    if is_partial or not stat_breakdown or scored_stat_count < 3:
        return None

    # Flatten to (phase, stat, z), deduplicate by stat keeping most extreme z per stat
    best_per_stat: dict[str, tuple[str, float]] = {}   # stat → (phase, z)
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

    went_well = [_make_went_well_entry(phase, stat, z, phase_stats)
                 for stat, phase, z in positives[:3]]
    hurt_most = [_make_hurt_most_entry(phase, stat, z, phase_stats)
                 for stat, phase, z in negatives[:3]]
    work_on   = [_make_work_on_entry(phase, stat, z, position, weakest_phase)
                 for stat, phase, z in negatives[:2]]

    return {"wentWell": went_well, "hurtMost": hurt_most, "workOn": work_on}


# ---------------------------------------------------------------------------
# UI v2 — enriched recurring patterns with win/loss evidence
# ---------------------------------------------------------------------------

def _pattern_summary(label: str, frequency: int, total: int, is_strength: bool) -> str:
    pct = round(frequency / max(total, 1) * 100)
    direction = "strength" if is_strength else "weakness"
    if frequency >= max(total * 0.7, 3):
        consistency = "consistently"
    elif frequency >= max(total * 0.5, 3):
        consistency = "frequently"
    else:
        consistency = "repeatedly"
    if is_strength:
        return (
            f"You {consistency} show above-benchmark {label} — it appeared as a strength "
            f"in {frequency} of your last {total} matches ({pct}%). "
            f"This is one of your more reliable positive patterns."
        )
    else:
        return (
            f"{label} appeared as a persistent {direction} in {frequency} of your last "
            f"{total} matches ({pct}%). "
            f"This is a recurring gap that shows up across different heroes and game states."
        )


def _win_loss_interpretation(label: str, is_strength: bool,
                              has_wins: bool, has_losses: bool) -> str | None:
    if not has_wins or not has_losses:
        return None
    if is_strength:
        return (
            f"In winning games, this {label} strength often combined with better overall impact "
            f"conversion. In losses, the edge was still present but wasn't enough to overcome "
            f"other deficits — suggesting it's a consistent positive but not a deciding factor alone."
        )
    else:
        return (
            f"In losses where {label} was flagged, the gap was more pronounced and likely "
            f"contributed to the result. Even in some wins this area underperformed, "
            f"confirming it as a persistent structural weakness rather than a situational one."
        )


def generate_recurring_pattern_entries(
    match_records: list[dict],
    threshold: int = 3,
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

        return {
            "label":                 label,
            "frequency":             frequency,
            "totalMatches":          total,
            "isStrength":            is_strength,
            "summary":               _pattern_summary(label, frequency, total, is_strength),
            "whyItMatters":          _STAT_WHY_MATTERS.get(label, "This metric reflects role effectiveness."),
            "winExample":            _ex(win_ex),
            "lossExample":           _ex(loss_ex),
            "winLossInterpretation": _win_loss_interpretation(label, is_strength, bool(wins), bool(losses)),
        }

    for label, count in s_counter.most_common(3):
        if count >= threshold:
            entries.append(_make_entry(label, count, is_strength=True))

    for label, count in w_counter.most_common(3):
        if count >= threshold:
            entries.append(_make_entry(label, count, is_strength=False))

    return entries
