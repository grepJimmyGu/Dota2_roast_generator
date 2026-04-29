"""
Benchmark transformation: converts raw Stratz heroStats scalars into the
{stat_key: {avg, stdDev}} format consumed by the scoring layer.
Also handles game-state multiplier application.
"""
from __future__ import annotations
from dota_core.benchmarks.priors import VACANCY_BENCHMARKS, AGGRESSION_BENCHMARKS, HEALING_BENCHMARKS


def build_phase_benchmarks(raw_bm: dict, phase: str, position: int = 0) -> dict[str, dict]:
    """
    Convert a raw Stratz heroStats response dict into scoring-ready benchmark format.

    raw_bm: direct API response for a specific (hero/position, bracket, time window).
    phase:  "lane" | "mid" | "closing" — selects the right heuristic priors.

    stdDev is estimated as 30% of avg (reasonable prior — Stratz doesn't expose it).
    """
    def _entry(val) -> dict | None:
        if val is None:
            return None
        avg = float(val)
        return {"avg": avg, "stdDev": avg * 0.30}

    phase_bm: dict[str, dict] = {}

    # Direct mappings: Stratz field → scoring stat key
    stat_map = {
        "damage_dealt":     raw_bm.get("heroDamage"),
        "tower_damage":     raw_bm.get("towerDamage"),
        "kills_in_phase":   raw_bm.get("kills"),
        "deaths_in_phase":  raw_bm.get("deaths"),
        "assists_in_phase": raw_bm.get("assists"),
        "last_hits":        raw_bm.get("cs"),
        "denies":           raw_bm.get("dn"),
    }
    for stat_key, val in stat_map.items():
        entry = _entry(val)
        if entry:
            phase_bm[stat_key] = entry

    # net_worth_gain: Stratz doesn't expose networth per phase.
    # Proxy: heroDamage × 4.0 (networth is typically ~4× damage dealt per phase window).
    dmg = raw_bm.get("heroDamage")
    if dmg:
        nw_avg = float(dmg) * 4.0
        phase_bm["net_worth_gain"] = {"avg": nw_avg, "stdDev": nw_avg * 0.30}

    # Heuristic priors for stats Stratz doesn't expose
    phase_bm["vacancy_time"] = VACANCY_BENCHMARKS[phase]
    phase_bm["aggression"]   = AGGRESSION_BENCHMARKS[phase]

    # Healing prior: only populated for positions that appear in HEALING_BENCHMARKS.
    # Non-healer heroes return healing=None in extract_phase_stats and skip this entry.
    healing_prior = HEALING_BENCHMARKS.get(phase, {}).get(position)
    if healing_prior:
        phase_bm["healing"] = healing_prior

    return phase_bm


def apply_multiplier(phase_bm: dict, multiplier: float) -> dict:
    """
    Scale benchmark avg values by the game-state multiplier.
    Stomp wins raise the bar; stomp losses lower it. No-op when multiplier == 1.0.
    """
    if multiplier == 1.0:
        return phase_bm
    adjusted: dict = {}
    for stat, entry in phase_bm.items():
        avg = entry.get("avg")
        std = entry.get("stdDev")
        if avg is not None:
            adjusted[stat] = {
                "avg":    avg * multiplier,
                "stdDev": std * multiplier if std else None,
            }
        else:
            adjusted[stat] = entry
    return adjusted
