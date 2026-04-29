"""
Internal domain models.

Use dataclasses for pure domain objects that stay inside the service layer.
Pydantic is reserved for API I/O (see dota_core/api/schemas.py).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlayerProfile:
    steam_account_id: int
    name: Optional[str]
    avatar_url: Optional[str]
    match_count: Optional[int]
    win_count: Optional[int]


@dataclass
class MatchSummary:
    """Flat summary of a single ranked match row."""
    match_id: int
    start_time: int
    duration_seconds: int
    average_rank: Optional[int]
    won: Optional[bool]
    hero_id: int
    position: int
    kills: Optional[int]
    deaths: Optional[int]
    assists: Optional[int]
    gold_per_minute: Optional[float]
    experience_per_minute: Optional[float]
    hero_damage: Optional[int]
    hero_healing: Optional[int]
    tower_damage: Optional[int]
    imp: Optional[float]


@dataclass
class PhaseStats:
    """Per-phase extracted stat values for one player."""
    net_worth_gain: Optional[float]
    damage_dealt: Optional[float]
    healing: Optional[float]
    tower_damage: Optional[float]
    last_hits: Optional[float]
    denies: Optional[float]
    kills_in_phase: Optional[float]
    assists_in_phase: Optional[float]
    vacancy_time: Optional[float] = None    # carry only
    aggression: Optional[float] = None      # offlane only


@dataclass
class PhaseScore:
    """Scored output for one phase (0–100 each track)."""
    position_score: Optional[float]
    hero_score: Optional[float]


@dataclass
class MatchScore:
    """Full scored output for a single match."""
    match_id: int
    early_game: PhaseScore
    mid_game: PhaseScore
    late_game: PhaseScore
    overall_position_score: Optional[float]
    overall_hero_score: Optional[float]
    game_closeness: Optional[float]


@dataclass
class HeroPerformance:
    """Aggregated ranked stats for a player on one hero."""
    hero_id: int
    win_count: int
    match_count: int
    avg_kills: Optional[float]
    avg_deaths: Optional[float]
    avg_assists: Optional[float]
    avg_gold_per_minute: Optional[float]
    avg_experience_per_minute: Optional[float]
    imp: Optional[float]


@dataclass
class PlayerOverview:
    """
    Top-level domain object for the player dashboard.

    TODO: aggregate scoring fields (average_overall_score, strongest_phase, weakest_phase,
    best_heroes, recent_trend) require a scored match history to be computed.
    Wire these up once scoring is persisted via a DB or cache layer.
    """
    profile: PlayerProfile
    recent_matches: list[MatchSummary] = field(default_factory=list)
    hero_performance: list[HeroPerformance] = field(default_factory=list)
    scored_matches: list[MatchScore] = field(default_factory=list)


@dataclass
class MatchDetailAnalysis:
    """
    Full per-match analysis object used inside the service layer.

    TODO: top_strengths and top_weaknesses require ranking stats by z-score delta —
    build this once the scoring layer exposes per-stat z-scores alongside aggregates.
    """
    summary: MatchSummary
    score: MatchScore
    phase_stats: dict[str, PhaseStats]  # {"lane": ..., "mid": ..., "closing": ...}
