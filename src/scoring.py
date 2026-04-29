# DEPRECATED: split into src/dota_core/scoring/{weights,features,adjusters,score_match}.py
"""
Performance scoring — three phases, position-aware weights.

Phase boundaries (minutes):
  Lane stage : 0–15
  Mid game   : 15–30
  Closing    : 30+

Positions:
  1 = Safe Lane Carry
  2 = Mid
  3 = Offlane
  4 = Soft Support
  5 = Hard Support
"""

from __future__ import annotations
import pandas as pd
from src.constants import LANE_END, MID_END

# ---------------------------------------------------------------------------
# Heroes where low HP during lane is intentional — exclude health score.
# Huskar (59): gains attack speed / damage from low HP (Berserker's Blood).
# Add others here as needed (use Valve/Stratz hero IDs).
# ---------------------------------------------------------------------------
HEALTH_EXCEPTION_HEROES: frozenset[int] = frozenset({
    59,   # Huskar
})

# ---------------------------------------------------------------------------
# Per-phase, per-position stat weights
# Each dict maps stat_key -> weight. Weights within a phase sum to 1.0 in abs.
# Negative weight = lower is better (deaths).
# ---------------------------------------------------------------------------

# Stats derived from per-minute arrays (summed over phase window):
#   net_worth_gain, last_hits, denies, xp_gain,
#   damage_dealt, healing, tower_damage,
#   kills_in_phase, deaths_in_phase, assists_in_phase
#
# Stats from overall match data (used when per-minute is unavailable):
#   goldPerMinute, experiencePerMinute, heroDamage, heroHealing, towerDamage,
#   kills, deaths, assists, imp

PHASE_WEIGHTS: dict[str, dict[int, dict[str, float]]] = {
    "lane": {
        # health_status = avg HP% during 0-15 min vs. hero benchmark.
        # Excluded automatically for heroes in HEALTH_EXCEPTION_HEROES.
        # tower_damage in lane = early objective pressure / dive follow-up.
        1: {  # Carry — farm + health + opportunistic tower pressure
            "net_worth_gain":  0.25,
            "last_hits":       0.21,
            "denies":          0.06,
            "xp_gain":         0.06,
            "deaths_in_phase": -0.13,
            "health_status":   0.13,
            "tower_damage":    0.06,
            "vacancy_time":    -0.10,  # idle farming time — low weight early (fighting is ok)
        },
        2: {  # Mid — farm + aggression + rune control + tower pressure
            "net_worth_gain":  0.16,
            "last_hits":       0.13,
            "kills_in_phase":  0.14,
            "xp_gain":         0.12,
            "deaths_in_phase": -0.13,
            "health_status":   0.12,
            "tower_damage":    0.10,
            "rune_control":    0.10,
        },
        3: {  # Offlane — harassment pressure + survival + lane presence
            "xp_gain":         0.18,
            "deaths_in_phase": -0.17,
            "kills_in_phase":  0.13,
            "assists_in_phase":0.12,
            "health_status":   0.18,
            "tower_damage":    0.10,
            "aggression":      0.12,  # freq × per-instance damage — sustained harassment quality
        },
        4: {  # Soft support
            "assists_in_phase":0.20,
            "kills_in_phase":  0.14,
            "deaths_in_phase": -0.14,
            "healing":         0.10,
            "xp_gain":         0.10,
            "health_status":   0.12,
            "tower_damage":    0.05,
            "vision_control":  0.15,
        },
        5: {  # Hard support
            "assists_in_phase":0.18,
            "deaths_in_phase": -0.14,
            "healing":         0.14,
            "kills_in_phase":  0.09,
            "denies":          0.12,
            "health_status":   0.13,
            "tower_damage":    0.05,
            "vision_control":  0.15,
        },
    },
    "mid": {
        # Tower damage: 15-20% — objectives become the primary win condition
        1: {  # Carry — farm + early objective takes to accelerate lead
            "net_worth_gain":  0.23,
            "damage_dealt":    0.19,
            "kills_in_phase":  0.11,
            "deaths_in_phase": -0.11,
            "tower_damage":    0.13,
            "assists_in_phase":0.08,
            "vacancy_time":    -0.15,  # mid-game idle time is costly — items scale exponentially
        },
        2: {  # Mid — snowball through kills + tower pressure
            "kills_in_phase":  0.22,
            "damage_dealt":    0.18,
            "assists_in_phase":0.13,
            "tower_damage":    0.20,
            "deaths_in_phase": -0.17,
            "net_worth_gain":  0.10,
        },
        3: {  # Offlane — objective focus + sustained fight pressure
            "tower_damage":    0.23,
            "assists_in_phase":0.18,
            "kills_in_phase":  0.11,
            "deaths_in_phase": -0.13,
            "healing":         0.09,
            "aggression":      0.18,  # mid-game fights — freq + per-hit quality matters more
            "damage_dealt":    0.08,  # keep a small total damage signal alongside aggression
        },
        4: {  # Soft support
            "assists_in_phase":0.21,
            "kills_in_phase":  0.11,
            "deaths_in_phase": -0.15,
            "healing":         0.14,
            "damage_dealt":    0.11,
            "tower_damage":    0.13,
            "vision_control":  0.15,
        },
        5: {  # Hard support
            "assists_in_phase":0.23,
            "healing":         0.19,
            "deaths_in_phase": -0.15,
            "kills_in_phase":  0.07,
            "tower_damage":    0.13,
            "damage_dealt":    0.08,
            "vision_control":  0.15,
        },
    },
    "closing": {
        # Tower damage: 20-25% — winning = converting fights into objectives
        1: {  # Carry — damage output + pushing won fights into buildings
            "damage_dealt":    0.22,
            "net_worth_gain":  0.16,
            "kills_in_phase":  0.13,
            "deaths_in_phase": -0.13,
            "tower_damage":    0.16,
            "vacancy_time":    -0.20,  # late game idle = catastrophic — every second not farming = lost items
        },
        2: {  # Mid — damage + leading objective takes
            "damage_dealt":    0.25,
            "kills_in_phase":  0.17,
            "assists_in_phase":0.13,
            "tower_damage":    0.22,
            "deaths_in_phase": -0.23,
        },
        3: {  # Offlane — initiate + convert fights into objectives
            "tower_damage":    0.22,
            "assists_in_phase":0.18,
            "deaths_in_phase": -0.15,
            "kills_in_phase":  0.08,
            "healing":         0.08,
            "aggression":      0.22,  # closing — sustained fight pressure is the offlane's core identity
            "damage_dealt":    0.07,  # residual total damage signal
        },
        4: {  # Soft support
            "assists_in_phase":0.22,
            "healing":         0.18,
            "tower_damage":    0.13,
            "kills_in_phase":  0.07,
            "deaths_in_phase": -0.12,
            "damage_dealt":    0.13,
            "vision_control":  0.15,
        },
        5: {  # Hard support
            "healing":         0.25,
            "assists_in_phase":0.23,
            "tower_damage":    0.13,
            "deaths_in_phase": -0.15,
            "kills_in_phase":  0.09,
            "vision_control":  0.15,
        },
    },
}

# Phase weights for the final overall score
PHASE_OVERALL_WEIGHTS = {"lane": 0.30, "mid": 0.35, "closing": 0.35}


# ---------------------------------------------------------------------------
# Phase stat extraction
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
    Falls back to raw health average (relative to hero benchmark) if max_health is absent.
    Returns a value in [0.0, 1.0], or None if data unavailable.
    """
    if health is None:
        return None

    hp_slice = health[start:end]
    if not hp_slice:
        return None

    if max_health is not None:
        max_slice = max_health[start:end]
        ratios = [
            h / m for h, m in zip(hp_slice, max_slice)
            if m and m > 0
        ]
        return sum(ratios) / len(ratios) if ratios else None

    # No maxHealthPerMinute — return raw avg HP (z-scored against benchmark later)
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

    damage_frequency   : fraction of phase minutes with any hero damage (0–1).
                         Measures sustained harassment presence.
    avg_damage_per_instance : total damage dealt / number of damage instances.
                         Measures the quality/weight of each spell or hit.
                         Sourced from heroDamageReport.dealtTotal.instances when
                         available; falls back to avg damage per active minute.

    Multiplying the two rewards players who harass often AND hit hard each time.
    A player who bursts once (low freq, high per-instance) or tickles constantly
    (high freq, low per-instance) both score lower than sustained heavy pressure.
    """
    if damage_per_min is None:
        return None

    window = damage_per_min[start:end]
    if not window:
        return None

    total_window = float(sum(window))
    active_minutes = sum(1 for d in window if d > 0)
    total_minutes = len(window)

    if active_minutes == 0:
        return 0.0

    damage_frequency = active_minutes / total_minutes  # 0–1

    # Per-instance damage: prefer heroDamageReport if available
    avg_per_instance: float | None = None
    if damage_report:
        dealt = damage_report.get("dealtTotal") or {}
        instances_total = dealt.get("instances")
        hp_total = dealt.get("hp")
        if instances_total and hp_total and instances_total > 0:
            # Scale full-game instances proportionally to this phase window
            phase_fraction = (min(end, duration_min) - start) / duration_min if end else (duration_min - start) / duration_min
            phase_instances = max(1, instances_total * phase_fraction)
            avg_per_instance = total_window / phase_instances

    # Fallback: average damage per active minute (proxy for per-hit quality)
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

    Handles both cumulative arrays (diffs to get per-minute counts) and
    already-incremental arrays. Assumes cumulative if values are non-decreasing.
    """
    if last_hits_per_min is None:
        return None

    window = last_hits_per_min[start:end]
    if not window:
        return None

    # Detect cumulative vs per-minute by checking monotonicity
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
    Compute a composite vision control score for a phase window.

    Ward events have: {time: int (seconds), type: "OBSERVER"|"SENTRY", isPlanted: bool}
      - isPlanted=True  → ward placed by this player
      - isPlanted=False → enemy ward destroyed by this player (deward)

    Composite = observer_placed * 1.0 + sentry_placed * 0.6 + dewards * 1.5
    Sentries are weighted lower (reactive); dewards are weighted highest (active vision denial).
    """
    if ward_events is None:
        return None

    phase_events = [e for e in ward_events if start_sec <= e.get("time", 0) < end_sec]
    if not phase_events:
        return 0.0

    observer_placed = sum(
        1 for e in phase_events
        if e.get("isPlanted") and e.get("type") == "OBSERVER"
    )
    sentry_placed = sum(
        1 for e in phase_events
        if e.get("isPlanted") and e.get("type") == "SENTRY"
    )
    dewards = sum(1 for e in phase_events if not e.get("isPlanted"))

    return observer_placed * 1.0 + sentry_placed * 0.6 + dewards * 1.5


def _count_rune_pickups(rune_pickups: list[dict] | None, start_sec: int, end_sec: int) -> float | None:
    """
    Count runes picked up within [start_sec, end_sec).
    rune_pickups is a list of {time: int (seconds), rune: str} events.
    """
    if rune_pickups is None:
        return None
    return float(sum(1 for r in rune_pickups if start_sec <= r.get("time", 0) < end_sec))


def extract_phase_stats(player_stats: dict, duration_seconds: int, hero_id: int = 0, position: int = 0) -> dict[str, dict[str, float | None]]:
    """
    Slice per-minute stat arrays into lane / mid / closing phase buckets.
    Returns {phase: {stat_key: value}}.
    """
    s = player_stats.get("stats", {}) or {}
    duration_min = duration_seconds // 60

    networth   = s.get("networthPerMinute")
    damage     = s.get("heroDamagePerMinute")
    healing    = s.get("healPerMinute")
    tower      = s.get("towerDamagePerMinute")
    last_hits  = s.get("lastHitsPerMinute")       # corrected field name
    denies     = s.get("deniesPerMinute")          # corrected field name
    # xp, health, rune, ward per-minute arrays not available in Stratz API

    # Event-based (inside stats, with {time} in seconds)
    kill_events   = s.get("killEvents") or []
    assist_events = s.get("assistEvents") or []

    is_mid     = position == 2
    is_support = position in (4, 5)
    is_carry   = position == 1
    is_offlane = position == 3

    def _count_events(events: list[dict], start_sec: int, end_sec: int) -> float:
        return float(sum(1 for e in events if start_sec <= (e.get("time") or 0) < end_sec))

    def phase_stats(
        start: int,
        end: int | None,
        include_vacancy: bool = False,
        include_aggression: bool = False,
    ) -> dict[str, float | None]:
        start_sec = start * 60
        end_sec   = (end * 60) if end is not None else duration_seconds

        stats = {
            "net_worth_gain":   _sum_window(networth, start, end),
            "damage_dealt":     _sum_window(damage, start, end),
            "healing":          _sum_window(healing, start, end),
            "tower_damage":     _sum_window(tower, start, end),
            "last_hits":        _sum_window(last_hits, start, end),
            "denies":           _sum_window(denies, start, end),
            "kills_in_phase":   _count_events(kill_events, start_sec, end_sec),
            "assists_in_phase": _count_events(assist_events, start_sec, end_sec),
            # deaths_in_phase: not directly available per phase from Stratz;
            # overall deaths from match row used in weight table as fallback
        }
        if include_vacancy:
            stats["vacancy_time"] = _vacancy_fraction(last_hits, start, end)
        if include_aggression:
            stats["aggression"] = _aggression_score(damage, None, start, end, duration_min)
        return stats

    closing_end = min(duration_min, len(networth)) if networth else None

    return {
        "lane":    phase_stats(0, LANE_END,          include_vacancy=is_carry, include_aggression=is_offlane),
        "mid":     phase_stats(LANE_END, MID_END,    include_vacancy=is_carry, include_aggression=is_offlane),
        "closing": phase_stats(MID_END, closing_end, include_vacancy=is_carry, include_aggression=is_offlane),
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _zscore(value: float | None, avg: float | None, std: float | None) -> float | None:
    if value is None or avg is None or std is None or std == 0:
        return None
    return max(-3.0, min(3.0, (value - avg) / std))


def _scale(z: float) -> float:
    """Map z-score range [-3, 3] to [0, 100]."""
    return round((z + 3) / 6 * 100, 2)


def _weighted_score(
    stats: dict[str, float | None],
    benchmarks: dict,
    weights: dict[str, float],
) -> float | None:
    """
    Compute a weighted z-score based performance score (0–100).
    benchmarks: {stat_key: {avg, stdDev}} — real phase-specific values from Stratz.
    """
    total_weight = 0.0
    weighted_sum = 0.0

    for stat, weight in weights.items():
        player_val = stats.get(stat)
        bm = benchmarks.get(stat, {})
        avg = bm.get("avg")
        std = bm.get("stdDev")

        z = _zscore(player_val, avg, std)
        if z is None:
            continue

        weighted_sum += weight * z
        total_weight += abs(weight)

    if total_weight == 0:
        return None

    return _scale(weighted_sum / total_weight)


def build_phase_benchmarks(raw_bm: dict, phase: str) -> dict:
    """
    Convert raw Stratz heroStats scalar fields into {stat_key: {avg, stdDev}} format.
    raw_bm is the direct API response for a specific phase window (minTime/maxTime already applied).
    stdDev is estimated as 30% of avg (reasonable prior — Stratz doesn't expose it).
    """
    def _entry(val) -> dict | None:
        if val is None:
            return None
        avg = float(val)
        return {"avg": avg, "stdDev": avg * 0.30}

    phase_bm: dict[str, dict] = {}

    # Direct mappings from Stratz field → scoring stat key
    stat_map = {
        "damage_dealt":     raw_bm.get("heroDamage"),
        "tower_damage":     raw_bm.get("towerDamage"),
        "kills_in_phase":   raw_bm.get("kills"),
        "assists_in_phase": raw_bm.get("assists"),
        "last_hits":        raw_bm.get("cs"),
        "denies":           raw_bm.get("dn"),
    }
    for stat_key, val in stat_map.items():
        entry = _entry(val)
        if entry:
            phase_bm[stat_key] = entry

    # net_worth_gain: Stratz doesn't expose networth per phase, use heroDamage as order-of-magnitude
    # proxy scaled 4× (networth is typically ~4× damage dealt in a phase window)
    dmg = raw_bm.get("heroDamage")
    if dmg:
        nw_avg = float(dmg) * 4.0
        phase_bm["net_worth_gain"] = {"avg": nw_avg, "stdDev": nw_avg * 0.30}

    # Heuristic benchmarks for stats Stratz doesn't expose
    _VACANCY_BENCHMARKS = {
        "lane":    {"avg": 0.35, "stdDev": 0.12},
        "mid":     {"avg": 0.25, "stdDev": 0.10},
        "closing": {"avg": 0.20, "stdDev": 0.08},
    }
    phase_bm["vacancy_time"] = _VACANCY_BENCHMARKS[phase]

    _AGGRESSION_BENCHMARKS = {
        "lane":    {"avg": 66.0,  "stdDev": 23.0},
        "mid":     {"avg": 126.0, "stdDev": 44.0},
        "closing": {"avg": 188.0, "stdDev": 66.0},
    }
    phase_bm["aggression"] = _AGGRESSION_BENCHMARKS[phase]

    return phase_bm


def game_closeness(match_row: dict) -> float:
    """
    Measure how one-sided the game was.
    Returns 0.0 (complete stomp) → 1.0 (perfectly even kills).
    Uses kill ratio: min(team_kills, enemy_kills) / max(team_kills, enemy_kills).
    """
    r = match_row.get("radiant_kills") or 0
    d = match_row.get("dire_kills") or 0
    total = r + d
    if total == 0:
        return 1.0
    return round(min(r, d) / max(r, d), 4)


def benchmark_multiplier(closeness: float, won: bool | None) -> float:
    """
    Scale benchmarks based on game state:
    - Stomp win  (closeness→0, won=True):  multiplier > 1 — expect more from an easy game
    - Stomp loss (closeness→0, won=False): multiplier < 1 — expect less when heavily suppressed
    - Close game (closeness→1):            multiplier = 1 — standard benchmark
    Max adjustment ±25%.
    """
    if won is None:
        return 1.0
    stomp_factor = 1.0 - closeness          # 0 = even, 1 = complete stomp
    direction = 1.0 if won else -1.0
    return round(1.0 + direction * stomp_factor * 0.25, 4)


def _apply_multiplier(phase_bm: dict, multiplier: float) -> dict:
    """Scale avg values in a phase benchmark dict by the game state multiplier."""
    if multiplier == 1.0:
        return phase_bm
    adjusted = {}
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


def score_match(
    match_row: dict,
    player_detail: dict | None,
    phase_benchmarks: dict[str, dict[str, dict | None]],
) -> dict[str, float | None]:
    """
    Compute per-phase position and hero scores, normalized for game state.

    phase_benchmarks: {phase: {"hero": bm, "position": bm}} from get_phase_benchmarks()

    Returns dict with keys:
      lane/mid/closing × position/hero scores + overall_position + overall_hero
    """
    position = max(1, min(5, int(match_row.get("position") or 1)))
    duration_sec = match_row.get("duration_seconds") or 0
    hero_id = int(match_row.get("heroId") or 0)
    won = match_row.get("won")

    result: dict[str, float | None] = {
        "lane_position_score":    None, "lane_hero_score":    None,
        "mid_position_score":     None, "mid_hero_score":     None,
        "closing_position_score": None, "closing_hero_score": None,
        "overall_position_score": None, "overall_hero_score": None,
        "game_closeness":         None,
    }

    if not player_detail or not player_detail.get("stats"):
        return result

    closeness  = game_closeness(match_row)
    multiplier = benchmark_multiplier(closeness, won)
    result["game_closeness"] = closeness

    phase_data = extract_phase_stats(player_detail, duration_sec, hero_id=hero_id, position=position)
    weights_map = PHASE_WEIGHTS

    pos_scores  = {}
    hero_scores = {}

    for phase in ("lane", "mid", "closing"):
        bm_pair = phase_benchmarks.get(phase, {})
        raw_hero_bm = bm_pair.get("hero")
        raw_pos_bm  = bm_pair.get("position")
        weights = weights_map[phase][position]
        stats   = phase_data[phase]

        if raw_pos_bm:
            pos_bm = _apply_multiplier(build_phase_benchmarks(raw_pos_bm, phase), multiplier)
            pos_scores[phase] = _weighted_score(stats, pos_bm, weights)
        else:
            pos_scores[phase] = None

        if raw_hero_bm:
            hero_bm = _apply_multiplier(build_phase_benchmarks(raw_hero_bm, phase), multiplier)
            hero_scores[phase] = _weighted_score(stats, hero_bm, weights)
        else:
            hero_scores[phase] = None

        result[f"{phase}_position_score"] = pos_scores[phase]
        result[f"{phase}_hero_score"]     = hero_scores[phase]

    for label, score_map in (("position", pos_scores), ("hero", hero_scores)):
        valid = {p: s for p, s in score_map.items() if s is not None}
        if valid:
            w_sum = sum(PHASE_OVERALL_WEIGHTS[p] for p in valid)
            result[f"overall_{label}_score"] = round(
                sum(PHASE_OVERALL_WEIGHTS[p] * s for p, s in valid.items()) / w_sum, 2
            )

    return result


def score_matches(
    df: pd.DataFrame,
    detail_map: dict[int, dict],
    phase_benchmark_map: dict[int, dict[str, dict[str, dict | None]]],
) -> pd.DataFrame:
    """
    Add position/hero scores and game_closeness columns to df.

    Args:
        df: matches DataFrame from get_ranked_matches()
        detail_map: {match_id: player_detail_dict} from get_match_details()
        phase_benchmark_map: {match_id: {phase: {"hero": bm, "position": bm}}}
    """
    df = df.copy()
    scores = df.apply(
        lambda row: score_match(
            row.to_dict(),
            detail_map.get(row["match_id"]),
            phase_benchmark_map.get(row["match_id"], {}),
        ),
        axis=1,
        result_type="expand",
    )
    return pd.concat([df, scores], axis=1)
