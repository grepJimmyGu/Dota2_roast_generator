"""
Aggregate stats across last N matches.

Maps to spec: packages/core/analysis/multi_match_summary.py
"""
from __future__ import annotations
from collections import Counter
from dota_core.roast.models import PlayerMatchStats


ROLE_NAMES = {1: "carry", 2: "mid", 3: "offlane", 4: "pos4", 5: "pos5"}


def _avg(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return round(sum(clean) / len(clean), 2) if clean else None


def summarize_last_matches(matches: list[PlayerMatchStats]) -> dict:
    """
    Compute aggregate stats across all provided matches.
    Uses safe defaults (None / 0) when fields are missing.
    """
    if not matches:
        return {}

    wins   = sum(1 for m in matches if m.won is True)
    losses = sum(1 for m in matches if m.won is False)
    total  = len(matches)

    # Hero frequency
    hero_counts: Counter = Counter()
    for m in matches:
        if m.hero_name:
            hero_counts[m.hero_name] += 1

    # Role distribution
    role_counts: Counter = Counter()
    for m in matches:
        role_counts[ROLE_NAMES.get(m.position, f"pos{m.position}")] += 1
    primary_role = role_counts.most_common(1)[0][0] if role_counts else "unknown"

    # Roast tag frequency (tag_ids from tag engine, not scoring labels)
    tag_counter: Counter = Counter()
    for m in matches:
        for tag in m.roast_tags:
            tag_counter[tag] += 1

    # Identify high-severity matches (overall score < 35 or 3+ weaknesses)
    high_severity = sum(
        1 for m in matches
        if (m.overall_score is not None and m.overall_score < 35) or len(m.weaknesses) >= 3
    )

    # Comeback throw: lost a game with early lead (early score > 60 but lost)
    comeback_throw = sum(
        1 for m in matches
        if m.won is False
        and m.early_position_score is not None
        and m.early_position_score > 60
    )

    # Low impact win: won but scored below 45
    low_impact_win = sum(
        1 for m in matches
        if m.won is True
        and m.overall_score is not None
        and m.overall_score < 45
    )

    return {
        "total_matches":               total,
        "wins":                        wins,
        "losses":                      losses,
        "win_rate":                    round(wins / total, 3) if total else 0,
        "primary_role":                primary_role,
        "role_distribution":           dict(role_counts),
        "most_played_heroes":          [h for h, _ in hero_counts.most_common(3)],
        "average_kills":               _avg([m.kills for m in matches]),
        "average_deaths":              _avg([m.deaths for m in matches]),
        "average_assists":             _avg([m.assists for m in matches]),
        "average_gpm":                 _avg([m.gold_per_min for m in matches]),
        "average_hero_damage":         _avg([m.hero_damage for m in matches]),
        "average_tower_damage":        _avg([m.tower_damage for m in matches]),
        "average_duration":            _avg([m.duration_min for m in matches]),
        "average_net_worth":           _avg([m.net_worth for m in matches]),
        "average_last_hits":           _avg([m.last_hits for m in matches]),
        "average_overall_score":       _avg([m.overall_score for m in matches]),
        # Fields not yet available in current data model (reserved for future data)
        "average_xpm":                        None,   # XPM not in MATCH_DETAILED query
        "average_teamfight_participation":    None,   # not stored
        "average_observer_wards":             None,   # not stored
        "average_sentry_wards":               None,   # not stored
        "average_stuns":                      None,   # not stored
        "average_net_worth_rank_team":        None,   # not stored
        "average_hero_damage_rank_team":      None,   # not stored
        "most_common_problem_tags":    [t for t, _ in tag_counter.most_common(5)],
        "high_severity_match_count":   high_severity,
        "comeback_throw_loss_count":   comeback_throw,
        "low_impact_win_count":        low_impact_win,
    }
