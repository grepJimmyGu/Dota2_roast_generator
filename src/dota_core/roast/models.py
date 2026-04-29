"""
Data models for the critique pipeline.

Maps to spec: packages/core/roast/critique_schema.py
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class PlayerMatchStats:
    """All per-match data available for one player from the DB."""
    match_id:   int
    hero_id:    int
    hero_name:  str | None
    position:   int          # 1–5
    won:        bool | None
    duration_min: float
    kills:      int | None
    deaths:     int | None
    assists:    int | None
    # Scores from MatchScore table
    overall_score:        float | None
    position_score:       float | None
    hero_score:           float | None
    early_position_score: float | None
    mid_position_score:   float | None
    late_position_score:  float | None
    weaknesses: list[str] = field(default_factory=list)   # scoring system labels (profile summary)
    strengths:  list[str] = field(default_factory=list)   # scoring system labels (profile summary)
    roast_tags: list[str] = field(default_factory=list)   # roast tag IDs (critique only)
    # From MatchDetail.raw_payload — None when detail not cached
    hero_damage:  float | None = None
    tower_damage: float | None = None
    net_worth:    float | None = None
    gold_per_min: float | None = None
    last_hits:    float | None = None


@dataclass
class LongformCritiqueOutput:
    """Structured output from the LLM critique generation."""
    title:             str
    primary_role:      str
    overall_verdict:   str
    critique:          str
    key_problem_tags:  list[str]
    evidence_used:     list[dict]
    final_punchline:   str
    tone:              str   # "light" | "medium" | "high"

    # TODO (Future RAG): attach high-quality example critiques, hero-specific
    # punchlines, and role-specific writing patterns to improve output quality.
