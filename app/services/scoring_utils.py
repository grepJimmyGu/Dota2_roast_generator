"""
Shared scoring utilities used by both player_service and match_service.
"""
from __future__ import annotations
from collections import defaultdict

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
