export interface MatchSummary {
  matchId: number;
  heroId: number;
  heroName: string | null;
  position: number;
  won: boolean | null;
  durationMinutes: number;
  kills: number | null;
  deaths: number | null;
  assists: number | null;
  overallPositionScore: number | null;
  overallHeroScore: number | null;
  gameCloseness: number | null;
  scoringPending: boolean;
}

export interface DataCompleteness {
  requestedMatchCount: number;
  fetchedDetailCount: number;
  scoredMatchCount: number;
  failedMatchCount: number;
}

export interface BestHero {
  heroId: number;
  heroName: string;
  avgScore: number;
  games: number;
}

export interface PlayerOverview {
  steamId: number;
  playerName: string | null;
  avatarUrl: string | null;
  rank: number | null;
  recentMatchCount: number;
  averageOverallScore: number | null;
  averagePositionScore: number | null;
  averageHeroScore: number | null;
  strongestPhase: string | null;
  weakestPhase: string | null;
  shortSummary: string | null;
  bestHeroes: BestHero[] | null;
  recentTrend: "improving" | "declining" | "stable" | null;
  isStale: boolean;
  refreshRecommended: boolean;
  lastRefreshedAt: string | null;
  dataCompleteness: DataCompleteness | null;
  recentMatches: MatchSummary[];
  // UI v1 — richer content
  playerNarrative: string | null;
  recurringStrengths: string[] | null;
  recurringWeaknesses: string[] | null;
  consistencyRating: "Consistent" | "Variable" | "Volatile" | null;
  performanceArchetype: string | null;
}

export interface PhaseScore {
  positionScore: number | null;
  heroScore: number | null;
}

export interface PhaseStatEntry {
  netWorth: number;
  heroDamage: number;
  towerDamage: number;
  lastHits: number;
  kills: number;
  deaths: number;
}

export interface MatchDetail {
  matchId: number;
  heroId: number;
  heroName: string | null;
  position: number;
  result: "win" | "loss" | null;
  durationMinutes: number;
  overallPositionScore: number | null;
  overallHeroScore: number | null;
  phaseBreakdown: {
    early_game: PhaseScore;
    mid_game: PhaseScore;
    late_game: PhaseScore;
  };
  gameCloseness: number | null;
  strongestPhase: string | null;
  weakestPhase: string | null;
  shortSummary: string | null;
  topStrengths: string[] | null;
  topWeaknesses: string[] | null;
  hasBenchmarkContext: boolean;
  isPartial: boolean;
  // UI v1 — richer content
  matchNarrative: string | null;
  phaseNarrative: { early_game?: string; mid_game?: string; late_game?: string } | null;
  biggestEdge: string | null;
  biggestLiability: string | null;
  improvementSuggestion: string | null;
  performanceProfile: string | null;
  phaseStats: {
    early_game?: PhaseStatEntry;
    mid_game?: PhaseStatEntry;
    late_game?: PhaseStatEntry;
  } | null;
}
