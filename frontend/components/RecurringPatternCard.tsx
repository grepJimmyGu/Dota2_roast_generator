"use client";

import { RecurringPatternEntry } from "@/lib/types";
import { useLanguage } from "@/contexts/LanguageContext";

interface Props {
  pattern: RecurringPatternEntry;
  steamId: number;
}

function ScorePill({ score }: { score: number | null }) {
  if (score === null) return null;
  const color = score >= 60 ? "text-green-400" : score >= 40 ? "text-yellow-400" : "text-red-400";
  return <span className={`tabular-nums text-xs font-medium ${color}`}>{score.toFixed(0)}</span>;
}

export default function RecurringPatternCard({ pattern, steamId }: Props) {
  const { t } = useLanguage();
  const borderColor = pattern.isStrength ? "border-green-800/40" : "border-red-800/40";
  const tagColor    = pattern.isStrength
    ? "bg-green-900/30 text-green-400"
    : "bg-red-900/30 text-red-400";
  const icon = pattern.isStrength ? "▲" : "▼";

  return (
    <div className={`bg-gray-900 rounded-xl p-4 border ${borderColor} flex flex-col gap-3`}>
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${tagColor}`}>
          {icon} {pattern.label}
        </span>
        <span className="text-xs text-gray-600">
          {t.appearsIn(pattern.frequency, pattern.totalMatches)}
        </span>
      </div>

      {/* Summary */}
      <p className="text-sm text-gray-300 leading-relaxed">{pattern.summary}</p>

      {/* Why it matters */}
      <p className="text-xs text-gray-500 italic">{pattern.whyItMatters}</p>

      {/* Win / Loss examples */}
      {(pattern.winExample || pattern.lossExample) && (
        <div className="flex gap-2 flex-wrap">
          {pattern.winExample && (
            <a
              href={`/matches/${pattern.winExample.matchId}?steamId=${steamId}`}
              className="flex items-center gap-1.5 bg-green-950/30 border border-green-800/30 rounded-lg px-2.5 py-1.5 text-xs text-green-400 hover:border-green-600/50 transition-colors"
            >
              <span className="text-gray-500">{t.winExample}:</span>
              <span>{pattern.winExample.heroName ?? `#${pattern.winExample.matchId}`}</span>
              <ScorePill score={pattern.winExample.overallScore} />
            </a>
          )}
          {pattern.lossExample && (
            <a
              href={`/matches/${pattern.lossExample.matchId}?steamId=${steamId}`}
              className="flex items-center gap-1.5 bg-red-950/30 border border-red-800/30 rounded-lg px-2.5 py-1.5 text-xs text-red-400 hover:border-red-600/50 transition-colors"
            >
              <span className="text-gray-500">{t.lossExample}:</span>
              <span>{pattern.lossExample.heroName ?? `#${pattern.lossExample.matchId}`}</span>
              <ScorePill score={pattern.lossExample.overallScore} />
            </a>
          )}
        </div>
      )}

      {/* Win/loss interpretation */}
      {pattern.winLossInterpretation && (
        <div className="border-t border-gray-800 pt-2">
          <p className="text-xs text-gray-500 mb-0.5">{t.winsVsLosses}</p>
          <p className="text-xs text-gray-400 leading-relaxed">{pattern.winLossInterpretation}</p>
        </div>
      )}
    </div>
  );
}
