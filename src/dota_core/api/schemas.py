"""
Pydantic response schemas — stable JSON contracts for the API surface.

Rules:
- All Optional fields that require aggregation or future logic are marked with TODO comments.
- Field names use camelCase to match mobile/web frontend conventions.
- Import these directly in FastAPI route response_model= parameters.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# UI v2 — richer interpretation schemas
# ---------------------------------------------------------------------------

class ScoreContextSchema(BaseModel):
    """Percentile context for a single score value."""
    score:        float
    benchmarkAvg: float = 50.0   # always 50 by construction of the z-score formula
    percentile:   float           # 0–100
    label:        str             # "Top 10%", "Above average", etc.


class AnalysisEntrySchema(BaseModel):
    """One item in a match analysis bucket (went well / hurt most / work on)."""
    title:        str
    detail:       str             # 2–3 sentence explanation
    phase:        Optional[str] = None
    whyItMatters: str
    takeaway:     str


class MatchAnalysisSchema(BaseModel):
    wentWell: list[AnalysisEntrySchema] = []
    hurtMost: list[AnalysisEntrySchema] = []
    workOn:   list[AnalysisEntrySchema] = []


class WinLossExampleSchema(BaseModel):
    matchId:      int
    heroName:     Optional[str] = None
    result:       str             # "win" | "loss"
    overallScore: Optional[float] = None


class RecurringPatternEntrySchema(BaseModel):
    """Enriched recurring strength or weakness with win/loss evidence."""
    label:                 str
    frequency:             int
    totalMatches:          int
    isStrength:            bool
    summary:               str
    whyItMatters:          str
    winExample:            Optional[WinLossExampleSchema] = None
    lossExample:           Optional[WinLossExampleSchema] = None
    winLossInterpretation: Optional[str] = None


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

class PhaseScoreSchema(BaseModel):
    positionScore: Optional[float] = None
    heroScore: Optional[float] = None


class PhaseBreakdownSchema(BaseModel):
    early_game: PhaseScoreSchema
    mid_game: PhaseScoreSchema
    late_game: PhaseScoreSchema


class DataCompletenessSchema(BaseModel):
    """Tracks how many matches were attempted, fetched, scored, and failed in a single request."""
    requestedMatchCount: int    # matches returned from the match list
    fetchedDetailCount: int     # matches for which per-minute detail was available
    scoredMatchCount: int       # matches that produced complete scores
    failedMatchCount: int       # matches that could not be scored (detail missing or scoring error)


# ---------------------------------------------------------------------------
# Player search result
# ---------------------------------------------------------------------------

class PlayerSearchResult(BaseModel):
    steamId: int
    playerName: Optional[str] = None
    avatarUrl: Optional[str] = None


# ---------------------------------------------------------------------------
# Match summary (used inside PlayerOverviewResponse.recentMatches)
# ---------------------------------------------------------------------------

class MatchSummarySchema(BaseModel):
    matchId: int
    heroId: int
    heroName: Optional[str] = None
    position: int
    won: Optional[bool] = None
    durationMinutes: float
    kills: Optional[int] = None
    deaths: Optional[int] = None
    assists: Optional[int] = None
    overallPositionScore: Optional[float] = None
    overallHeroScore: Optional[float] = None
    gameCloseness: Optional[float] = None
    scoringPending: bool = False


# ---------------------------------------------------------------------------
# Player overview — mobile/web dashboard endpoint
# ---------------------------------------------------------------------------

class PlayerOverviewResponse(BaseModel):
    steamId: int
    playerName: Optional[str] = None
    avatarUrl: Optional[str] = None
    rank: Optional[int] = None
    recentMatchCount: int = 0

    averageOverallScore: Optional[float] = None
    averagePositionScore: Optional[float] = None
    averageHeroScore: Optional[float] = None

    strongestPhase: Optional[str] = None
    weakestPhase: Optional[str] = None
    bestHeroes: Optional[list[dict]] = None
    recentTrend: Optional[str] = None
    shortSummary: Optional[str] = None

    # UI v1 — richer player-level content
    playerNarrative:      Optional[str] = None
    consistencyRating:    Optional[str] = None
    performanceArchetype: Optional[str] = None

    # UI v2 — score context + enriched recurring patterns
    scoreContext:      Optional[ScoreContextSchema] = None
    recurringPatterns: Optional[list[RecurringPatternEntrySchema]] = None

    # Cache / freshness metadata
    isStale: bool = False
    refreshRecommended: bool = False
    lastRefreshedAt: Optional[datetime] = None

    # Completeness metadata — always present, surfaces partial-result conditions
    dataCompleteness: Optional[DataCompletenessSchema] = None

    recentMatches: list[MatchSummarySchema] = []


# ---------------------------------------------------------------------------
# Match detail — per-match analysis screen endpoint
# ---------------------------------------------------------------------------

class MatchDetailResponse(BaseModel):
    matchId: int
    heroId: int
    heroName: Optional[str] = None
    position: int
    result: Optional[str] = None          # "win" | "loss" | None
    durationMinutes: float
    overallPositionScore: Optional[float] = None
    overallHeroScore: Optional[float] = None
    phaseBreakdown: PhaseBreakdownSchema
    gameCloseness: Optional[float] = None

    strongestPhase: Optional[str] = None
    weakestPhase: Optional[str] = None
    shortSummary: Optional[str] = None

    topStrengths: Optional[list[str]] = None
    topWeaknesses: Optional[list[str]] = None

    benchmarkContext: Optional[dict] = None
    hasBenchmarkContext: bool = False     # True when bracket/position context was resolved

    # True when scoring completed partially (some phase scores or overall scores are None)
    isPartial: bool = False

    # UI v1 — richer match-level content
    matchNarrative: Optional[str] = None
    phaseNarrative: Optional[dict] = None
    biggestEdge: Optional[str] = None
    biggestLiability: Optional[str] = None
    improvementSuggestion: Optional[str] = None
    performanceProfile: Optional[str] = None
    phaseStats: Optional[dict] = None

    # UI v2 — score context + deep analysis
    scoreContext:      Optional[ScoreContextSchema] = None
    heroScoreContext:  Optional[ScoreContextSchema] = None
    matchAnalysis:     Optional[MatchAnalysisSchema] = None


# ---------------------------------------------------------------------------
# Critique / roast — GET /players/{steam_id}/roast
# ---------------------------------------------------------------------------

class CritiqueEvidenceItem(BaseModel):
    match_id: str
    reason: str

class CritiqueResponse(BaseModel):
    title:            str
    primary_role:     str
    overall_verdict:  str
    critique:         str
    key_problem_tags: list[str]
    evidence_used:    list[CritiqueEvidenceItem]
    final_punchline:  str
    tone:             str   # "light" | "medium" | "high"


# ---------------------------------------------------------------------------
# Refresh result — POST /players/{steam_id}/refresh
# ---------------------------------------------------------------------------

class RefreshResponse(BaseModel):
    status: str
    matchCount: int
