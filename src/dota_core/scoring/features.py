"""
Phase stat extraction — slices per-minute arrays into lane / mid / closing buckets
and computes composite per-phase features (aggression, vacancy, vision, rune control).
"""
from __future__ import annotations
from dota_core.constants import LANE_END, MID_END


# ---------------------------------------------------------------------------
# Low-level per-minute array helpers
# ---------------------------------------------------------------------------

def _sum_window(arr: list[int | float] | None, start: int, end: int | None) -> float | None:
    if arr is None:
        return None
    sliced = arr[start:end]
    return float(sum(sliced)) if sliced else None


def _avg_hp_pct(
    health: list[int] | None,
    max_health: list[int] | None,
    start: int,
    end: int | None,
) -> float | None:
    """
    Compute average HP percentage over a time window.
    Uses healthPerMinute / maxHealthPerMinute arrays.
    Falls back to raw health average if max_health is absent.
    Returns [0.0, 1.0] or None if data unavailable.
    """
    if health is None:
        return None
    hp_slice = health[start:end]
    if not hp_slice:
        return None
    if max_health is not None:
        max_slice = max_health[start:end]
        ratios = [h / m for h, m in zip(hp_slice, max_slice) if m and m > 0]
        return sum(ratios) / len(ratios) if ratios else None
    return float(sum(hp_slice) / len(hp_slice))


def _aggression_score(
    damage_per_min: list[int] | None,
    damage_report: dict | None,
    start: int,
    end: int | None,
    duration_min: int,
) -> float | None:
    """
    Composite aggression metric for offlane players.

    = damage_frequency × avg_damage_per_instance

    damage_frequency:      fraction of phase minutes with any hero damage (0–1).
    avg_damage_per_instance: total damage / instances, sourced from heroDamageReport
                             when available; falls back to avg per active minute.

    Multiplying rewards players who harass often AND hit hard — a player who
    bursts once or tickles constantly both score lower than sustained heavy pressure.
    """
    if damage_per_min is None:
        return None
    window = damage_per_min[start:end]
    if not window:
        return None

    total_window   = float(sum(window))
    active_minutes = sum(1 for d in window if d > 0)
    total_minutes  = len(window)

    if active_minutes == 0:
        return 0.0

    damage_frequency = active_minutes / total_minutes

    avg_per_instance: float | None = None
    if damage_report:
        dealt = damage_report.get("dealtTotal") or {}
        instances_total = dealt.get("instances")
        hp_total = dealt.get("hp")
        if instances_total and hp_total and instances_total > 0:
            phase_fraction = (
                (min(end, duration_min) - start) / duration_min
                if end else (duration_min - start) / duration_min
            )
            phase_instances = max(1, instances_total * phase_fraction)
            avg_per_instance = total_window / phase_instances

    if avg_per_instance is None:
        avg_per_instance = total_window / active_minutes

    return damage_frequency * avg_per_instance


def _vacancy_fraction(
    last_hits_per_min: list[int] | None,
    start: int,
    end: int | None,
) -> float | None:
    """
    Fraction of minutes in [start, end) where the carry made zero last hits.
    Range [0.0, 1.0] — lower is better (carry was farming).
    Handles both cumulative and already-incremental arrays.
    """
    if last_hits_per_min is None:
        return None
    window = last_hits_per_min[start:end]
    if not window:
        return None

    is_cumulative = all(b >= a for a, b in zip(window, window[1:]))
    if is_cumulative:
        per_minute = [window[0]] + [window[i] - window[i - 1] for i in range(1, len(window))]
    else:
        per_minute = window

    vacant = sum(1 for lh in per_minute if lh == 0)
    return round(vacant / len(per_minute), 4)


def _vision_score(
    ward_events: list[dict] | None,
    start_sec: int,
    end_sec: int,
) -> float | None:
    """
    Composite vision control: observer×1.0 + sentry×0.6 + deward×1.5.
    Dewards weighted highest (active vision denial); sentries weighted lower (reactive).
    """
    if ward_events is None:
        return None
    phase_events = [e for e in ward_events if start_sec <= e.get("time", 0) < end_sec]
    if not phase_events:
        return 0.0

    observer_placed = sum(
        1 for e in phase_events if e.get("isPlanted") and e.get("type") == "OBSERVER"
    )
    sentry_placed = sum(
        1 for e in phase_events if e.get("isPlanted") and e.get("type") == "SENTRY"
    )
    dewards = sum(1 for e in phase_events if not e.get("isPlanted"))

    return observer_placed * 1.0 + sentry_placed * 0.6 + dewards * 1.5


def _count_rune_pickups(
    rune_pickups: list[dict] | None,
    start_sec: int,
    end_sec: int,
) -> float | None:
    """Count runes picked up within [start_sec, end_sec)."""
    if rune_pickups is None:
        return None
    return float(sum(1 for r in rune_pickups if start_sec <= r.get("time", 0) < end_sec))


# ---------------------------------------------------------------------------
# Phase stat assembly
# ---------------------------------------------------------------------------

def extract_phase_stats(
    player_stats: dict,
    duration_seconds: int,
    hero_id: int = 0,
    position: int = 0,
) -> dict[str, dict[str, float | None]]:
    """
    Slice per-minute stat arrays into lane / mid / closing phase buckets.
    Returns {phase: {stat_key: value}}.
    """
    s            = player_stats.get("stats", {}) or {}
    duration_min = duration_seconds // 60

    networth  = s.get("networthPerMinute")
    damage    = s.get("heroDamagePerMinute")
    healing   = s.get("healPerMinute")
    tower     = s.get("towerDamagePerMinute")
    last_hits = s.get("lastHitsPerMinute")
    denies    = s.get("deniesPerMinute")

    kill_events   = s.get("killEvents") or []
    assist_events = s.get("assistEvents") or []

    # Scalar totals from MATCH_DETAILED — prorated by phase duration fraction.
    # Prorating is more accurate than event-counting for assists/deaths (Stratz event arrays
    # miss passive-ability contributions and don't expose per-phase deaths at all).
    total_assists_scalar: int | None = player_stats.get("assists")
    total_deaths_scalar:  int | None = player_stats.get("deaths")

    is_carry   = position == 1
    is_offlane = position == 3

    def _count_events(events: list[dict], start_sec: int, end_sec: int) -> float:
        return float(sum(1 for e in events if start_sec <= (e.get("time") or 0) < end_sec))

    def _phase(
        start: int,
        end: int | None,
        include_vacancy: bool = False,
        include_aggression: bool = False,
    ) -> dict[str, float | None]:
        start_sec = start * 60
        end_sec   = (end * 60) if end is not None else duration_seconds

        # Assists: prorate from scalar total when available (avoids passive-ability undercounting).
        # Falls back to event counting if scalar is absent.
        phase_frac = (end_sec - start_sec) / duration_seconds

        if total_assists_scalar is not None:
            assists_val: float | None = round(total_assists_scalar * phase_frac, 2)
        else:
            assists_val = _count_events(assist_events, start_sec, end_sec)

        deaths_val: float | None = (
            round(total_deaths_scalar * phase_frac, 2)
            if total_deaths_scalar is not None else None
        )

        # Healing: return None when sum is 0 so non-healer heroes skip the benchmark entirely.
        raw_healing = _sum_window(healing, start, end)
        healing_val: float | None = raw_healing if raw_healing else None

        stats: dict[str, float | None] = {
            "net_worth_gain":   _sum_window(networth, start, end),
            "damage_dealt":     _sum_window(damage, start, end),
            "healing":          healing_val,
            "tower_damage":     _sum_window(tower, start, end),
            "last_hits":        _sum_window(last_hits, start, end),
            "denies":           _sum_window(denies, start, end),
            "kills_in_phase":   _count_events(kill_events, start_sec, end_sec),
            "assists_in_phase": assists_val,
            "deaths_in_phase":  deaths_val,
        }
        if include_vacancy:
            stats["vacancy_time"] = _vacancy_fraction(last_hits, start, end)
        if include_aggression:
            stats["aggression"] = _aggression_score(damage, None, start, end, duration_min)
        return stats

    closing_end = min(duration_min, len(networth)) if networth else None

    return {
        "early_game": _phase(0,        LANE_END,    include_vacancy=is_carry, include_aggression=is_offlane),
        "mid_game":   _phase(LANE_END, MID_END,     include_vacancy=is_carry, include_aggression=is_offlane),
        "late_game":  _phase(MID_END,  closing_end, include_vacancy=is_carry, include_aggression=is_offlane),
    }
