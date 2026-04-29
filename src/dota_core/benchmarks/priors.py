"""
Heuristic prior benchmarks for stats that Stratz does not expose via its API.

These are reasonable population-level estimates based on domain knowledge.
Replace with data-driven values as better sources become available.
"""

# Fraction of phase minutes where carry made zero last hits (lower = better farming)
VACANCY_BENCHMARKS: dict[str, dict[str, float]] = {
    "early_game": {"avg": 0.35, "stdDev": 0.12},
    "mid_game":   {"avg": 0.25, "stdDev": 0.10},
    "late_game":  {"avg": 0.20, "stdDev": 0.08},
}

# Aggression score = damage_frequency × avg_damage_per_instance (offlane, pos 3 only)
AGGRESSION_BENCHMARKS: dict[str, dict[str, float]] = {
    "early_game": {"avg": 66.0,  "stdDev": 23.0},
    "mid_game":   {"avg": 126.0, "stdDev": 44.0},
    "late_game":  {"avg": 188.0, "stdDev": 66.0},
}

# Healing benchmarks: applied only when player healing > 0 (non-healer heroes return None
# and are skipped naturally). Values represent HP healed in the phase window summed from
# healPerMinute arrays. stdDev is ~60% of avg to reflect wide variance across healer heroes.
# Only defined for positions where healing appears in PHASE_WEIGHTS (pos 3, 4, 5).
HEALING_BENCHMARKS: dict[str, dict[int, dict[str, float]]] = {
    "early_game": {
        3: {"avg": 600.0,  "stdDev": 400.0},
        4: {"avg": 1200.0, "stdDev": 750.0},
        5: {"avg": 1500.0, "stdDev": 950.0},
    },
    "mid_game": {
        3: {"avg": 1200.0, "stdDev": 750.0},
        4: {"avg": 2500.0, "stdDev": 1500.0},
        5: {"avg": 3000.0, "stdDev": 1800.0},
    },
    "late_game": {
        3: {"avg": 1800.0, "stdDev": 1100.0},
        4: {"avg": 3500.0, "stdDev": 2000.0},
        5: {"avg": 4500.0, "stdDev": 2600.0},
    },
}

# TODO: add health_status, vision_control, rune_control priors when data is available.
# These stats are currently not scored — they require per-minute arrays Stratz does not expose.
