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
    playerNarrative: Optional[str] = None          # multi-sentence profile synthesis
    recurringStrengths: Optional[list[str]] = None  # labels appearing 3+ times in recent matches
    recurringWeaknesses: Optional[list[str]] = None
    consistencyRating: Optional[str] = None         # "Consistent" | "Variable" | "Volatile"
    performanceArchetype: Optional[str] = None       # position-based label (e.g. "Space Creator")

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
    matchNarrative: Optional[str] = None                  # multi-sentence match analysis
    phaseNarrative: Optional[dict] = None                 # {phase: narrative_text}
    biggestEdge: Optional[str] = None                     # top strength with context sentence
    biggestLiability: Optional[str] = None                # top weakness with context sentence
    improvementSuggestion: Optional[str] = None           # one actionable next step
    performanceProfile: Optional[str] = None              # position-based archetype label
    phaseStats: Optional[dict] = None                     # {phase: {stat: value}} for display


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
