"""
Stat weights and scoring constants.

PHASE_WEIGHTS[phase][position] maps stat_key → weight.
Weights within a phase sum to 1.0 in absolute value.
Negative weight = lower is better (e.g. deaths).

INACTIVE STATS (in weights, silently skipped — no player value or benchmark available yet):
  xp_gain       — Stratz doesn't expose XP per phase; no per-minute XP array in MATCH_DETAILED.
  health_status — requires healthPerMinute arrays; not yet fetched in MATCH_DETAILED.
  rune_control  — requires runePickups events; not yet fetched in MATCH_DETAILED.
These contribute 0 to scoring and 0 to total_weight. They are placeholders for future data.
"""

# Heroes where low HP during lane is intentional — health_status excluded from scoring.
# Huskar (59): gains attack speed / damage from low HP (Berserker's Blood).
HEALTH_EXCEPTION_HEROES: frozenset[int] = frozenset({
    59,   # Huskar
})

PHASE_WEIGHTS: dict[str, dict[int, dict[str, float]]] = {
    "early_game": {
        # health_status = avg HP% during 0–12 min vs. hero benchmark.
        # tower_damage in lane = early objective pressure / dive follow-up.
        1: {  # Carry — farm efficiency + health + opportunistic tower pressure
            "net_worth_gain":  0.25,
            "last_hits":       0.21,
            "denies":          0.06,
            "xp_gain":         0.06,
            "deaths_in_phase": -0.13,
            "health_status":   0.13,
            "tower_damage":    0.06,
            "vacancy_time":    -0.10,  # idle farming penalty — low weight early (fighting is ok)
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
            "xp_gain":          0.18,
            "deaths_in_phase":  -0.17,
            "kills_in_phase":   0.13,
            "assists_in_phase": 0.12,
            "health_status":    0.18,
            "tower_damage":     0.10,
            "aggression":       0.12,  # freq × per-instance damage — sustained harassment quality
        },
        4: {  # Soft support
            "assists_in_phase": 0.23,  # +0.03 from healing reduction
            "kills_in_phase":   0.14,
            "deaths_in_phase":  -0.14,
            "healing":          0.07,  # reduced: not all supports heal
            "xp_gain":          0.10,
            "health_status":    0.12,
            "tower_damage":     0.05,
            "vision_control":   0.15,
        },
        5: {  # Hard support
            "assists_in_phase": 0.25,  # +0.07 from healing reduction
            "deaths_in_phase":  -0.14,
            "healing":          0.07,  # reduced: not all supports heal
            "kills_in_phase":   0.09,
            "denies":           0.12,
            "health_status":    0.13,
            "tower_damage":     0.05,
            "vision_control":   0.15,
        },
    },
    "mid_game": {
        # Tower damage: 15–20% — objectives become the primary win condition (13–40 min)
        1: {  # Carry — farm + early objective takes to accelerate lead
            "net_worth_gain":  0.23,
            "damage_dealt":    0.19,
            "kills_in_phase":  0.11,
            "deaths_in_phase": -0.11,
            "tower_damage":    0.13,
            "assists_in_phase":0.08,
            "vacancy_time":    -0.15,  # mid-game idle is costly — items scale exponentially
        },
        2: {  # Mid — snowball through kills + tower pressure
            "kills_in_phase":   0.22,
            "damage_dealt":     0.18,
            "assists_in_phase": 0.13,
            "tower_damage":     0.20,
            "deaths_in_phase":  -0.17,
            "net_worth_gain":   0.10,
        },
        3: {  # Offlane — objective focus + sustained fight pressure
            "tower_damage":     0.23,
            "assists_in_phase": 0.18,
            "kills_in_phase":   0.11,
            "deaths_in_phase":  -0.13,
            "healing":          0.09,
            "aggression":       0.18,  # mid-game fights — freq + per-hit quality matters more
            "damage_dealt":     0.08,  # residual total damage signal alongside aggression
        },
        4: {  # Soft support
            "assists_in_phase": 0.28,  # +0.07 from healing reduction
            "kills_in_phase":   0.11,
            "deaths_in_phase":  -0.15,
            "healing":          0.07,  # reduced: not all supports heal
            "damage_dealt":     0.11,
            "tower_damage":     0.13,
            "vision_control":   0.15,
        },
        5: {  # Hard support
            "assists_in_phase": 0.30,  # +0.07 from healing reduction
            "healing":          0.07,  # reduced: not all supports heal
            "deaths_in_phase":  -0.15,
            "kills_in_phase":   0.07,
            "tower_damage":     0.13,
            "damage_dealt":     0.08,
            "vision_control":   0.20,  # +0.05 from healing reduction
        },
    },
    "late_game": {
        # Tower damage: 20–25% — winning = converting fights into buildings
        1: {  # Carry — damage output + pushing won fights into buildings
            "damage_dealt":    0.22,
            "net_worth_gain":  0.16,
            "kills_in_phase":  0.13,
            "deaths_in_phase": -0.13,
            "tower_damage":    0.16,
            "vacancy_time":    -0.20,  # late game idle = catastrophic — every second = lost items
        },
        2: {  # Mid — damage + leading objective takes
            "damage_dealt":     0.25,
            "kills_in_phase":   0.17,
            "assists_in_phase": 0.13,
            "tower_damage":     0.22,
            "deaths_in_phase":  -0.23,
        },
        3: {  # Offlane — initiate + convert fights into objectives
            "tower_damage":     0.22,
            "assists_in_phase": 0.18,
            "deaths_in_phase":  -0.15,
            "kills_in_phase":   0.08,
            "healing":          0.08,
            "aggression":       0.22,  # closing — sustained fight pressure is offlane's core identity
            "damage_dealt":     0.07,  # residual total damage signal
        },
        4: {  # Soft support
            "assists_in_phase": 0.30,  # +0.08 from healing reduction
            "healing":          0.07,  # reduced: not all supports heal
            "tower_damage":     0.13,
            "kills_in_phase":   0.07,
            "deaths_in_phase":  -0.12,
            "damage_dealt":     0.13,
            "vision_control":   0.18,  # +0.03 from healing reduction
        },
        5: {  # Hard support
            "healing":          0.07,  # reduced: not all supports heal
            "assists_in_phase": 0.32,  # +0.09 from healing reduction
            "tower_damage":     0.13,
            "deaths_in_phase":  -0.15,
            "kills_in_phase":   0.09,
            "vision_control":   0.24,  # +0.09 from healing reduction
        },
    },
}

# Weights for rolling the three phase scores into a single overall score
PHASE_OVERALL_WEIGHTS: dict[str, float] = {
    "early_game": 0.30,
    "mid_game":   0.35,
    "late_game":  0.35,
}
