"use client";

import Link from "next/link";
import { MatchSummary } from "@/lib/types";
import { useLanguage } from "@/contexts/LanguageContext";

interface Props {
  match: MatchSummary;
  steamId: number;
}

function scoreColor(score: number | null): string {
  if (score === null) return "text-gray-500";
  if (score >= 65) return "text-green-400";
  if (score >= 50) return "text-yellow-400";
  if (score >= 35) return "text-orange-400";
  return "text-red-400";
}

export default function MatchCard({ match, steamId }: Props) {
  const { t } = useLanguage();

  const avgScore =
    match.overallPositionScore !== null && match.overallHeroScore !== null
      ? (match.overallPositionScore + match.overallHeroScore) / 2
      : match.overallPositionScore ?? match.overallHeroScore;

  return (
    <Link
      href={`/matches/${match.matchId}?steamId=${steamId}`}
      className="block bg-gray-800 hover:bg-gray-750 rounded-lg p-3 transition-colors"
    >
      <div className="flex items-center gap-3">
        <div
          className={`w-2 h-2 rounded-full flex-shrink-0 ${
            match.won === true ? "bg-green-400" : match.won === false ? "bg-red-400" : "bg-gray-600"
          }`}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="text-sm font-medium text-white truncate">
              {match.heroName ?? `Hero #${match.heroId}`}
            </span>
            <span className="text-xs text-gray-500 flex-shrink-0">
              {t.positions[match.position] ?? `Pos ${match.position}`}
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-0.5">
            {match.kills ?? "?"}/{match.deaths ?? "?"}/{match.assists ?? "?"} · {match.durationMinutes}m
            {match.scoringPending && (
              <span className="ml-2 text-gray-600 italic">{t.scoringPending}</span>
            )}
          </div>
        </div>
        <div className="flex-shrink-0 text-right">
          {match.scoringPending ? (
            <span className="text-xs text-gray-600">—</span>
          ) : (
            <span className={`text-sm font-semibold tabular-nums ${scoreColor(avgScore)}`}>
              {avgScore !== null ? avgScore.toFixed(1) : "—"}
            </span>
          )}
        </div>
        <svg className="w-4 h-4 text-gray-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </Link>
  );
}
