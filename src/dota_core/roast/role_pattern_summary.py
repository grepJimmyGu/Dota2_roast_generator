"""
Group matches by detected role and compute per-role critique angles.

Maps to spec: packages/core/analysis/role_pattern_summary.py
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dota_core.roast.models import PlayerMatchStats

ROLE_NAMES = {1: "carry", 2: "mid", 3: "offlane", 4: "pos4", 5: "pos5"}

# Role-specific critique angles — generated when the role appears in the data.
# TODO (Future RAG): replace with dynamically retrieved punchline patterns per role.
_CRITIQUE_ANGLES: dict[str, str] = {
    "carry":   "吃资源多，但输出和推塔转化不足",
    "mid":     "对线和中期节奏不足，地图影响力偏低",
    "offlane": "没有稳定开团和承伤，空间制造不足",
    "pos4":    "游走和控制贡献不足，节奏感弱",
    "pos5":    "视野和保人贡献不稳定，死亡偏多",
}

_SUPPORT_ROLES = {"pos4", "pos5"}


def _avg(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return round(sum(clean) / len(clean), 2) if clean else None


def summarize_role_patterns(matches: list[PlayerMatchStats]) -> dict[str, dict]:
    """
    Group matches by role and compute per-role aggregate stats and critique angle.
    Returns {role_name: {stats...}} — only includes roles that appear in data.
    """
    by_role: dict[str, list[PlayerMatchStats]] = defaultdict(list)
    for m in matches:
        role = ROLE_NAMES.get(m.position, f"pos{m.position}")
        by_role[role].append(m)

    result: dict[str, dict] = {}
    for role, ms in by_role.items():
        wins  = sum(1 for m in ms if m.won is True)
        total = len(ms)

        kills   = [m.kills   for m in ms if m.kills   is not None]
        deaths  = [m.deaths  for m in ms if m.deaths  is not None]
        assists = [m.assists for m in ms if m.assists is not None]
        kda = None
        if deaths and sum(deaths) > 0:
            kda = round((sum(kills or [0]) + sum(assists or [0])) / sum(deaths), 2)

        tag_counter: Counter = Counter()
        for m in ms:
            for t in m.weaknesses:
                tag_counter[t] += 1

        entry: dict = {
            "match_count":                  total,
            "win_rate":                     round(wins / total, 3) if total else 0,
            "avg_kda":                      kda,
            "avg_gpm":                      _avg([m.gold_per_min for m in ms]),
            "avg_hero_damage":              _avg([m.hero_damage  for m in ms]),
            "avg_tower_damage":             _avg([m.tower_damage for m in ms]),
            "avg_deaths":                   _avg([m.deaths       for m in ms]),
            "avg_xpm":                      None,   # not available
            "avg_teamfight_participation":  None,   # not available
            "avg_wards":                    None if role not in _SUPPORT_ROLES else None,
            "avg_stuns":                    None,
            "common_problem_tags":          [t for t, _ in tag_counter.most_common(3)],
            "role_specific_critique_angle": _CRITIQUE_ANGLES.get(role, "表现一般"),
        }
        result[role] = entry

    return result
