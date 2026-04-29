"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { MatchDetail } from "@/lib/types";
import ScoreBadge from "@/components/ScoreBadge";
import PhaseBar from "@/components/PhaseBar";
import { useLanguage } from "@/contexts/LanguageContext";
import { STAT_LABEL, Locale } from "@/lib/i18n";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function MatchDetailPage() {
  const { matchId }  = useParams<{ matchId: string }>();
  const searchParams = useSearchParams();
  const steamId      = searchParams.get("steamId");
  const router       = useRouter();
  const { t, locale } = useLanguage();

  const [data, setData]       = useState<MatchDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    if (!matchId || !steamId) {
      setError(t.matchNotFound);
      setLoading(false);
      return;
    }
    fetch(`${API}/matches/${matchId}?steam_id=${steamId}`)
      .then(async (res) => {
        if (res.status === 404) throw new Error("Match not found.");
        if (!res.ok) throw new Error(`Server error (${res.status}). Try again later.`);
        return res.json();
      })
      .then((json) => { setData(json); setLoading(false); })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, [matchId, steamId]);

  if (loading) return <LoadingSkeleton />;
  if (error)   return <ErrorState message={error} backLabel={t.goBack} onBack={() => router.back()} />;
  if (!data)   return null;

  const backHref = steamId ? `/players/${steamId}` : "/";

  // Translate backend stat labels to current locale
  function translateStat(label: string): string {
    return STAT_LABEL[label]?.[locale as Locale] ?? label;
  }

  return (
    <div className="flex flex-col gap-5">
      <Link href={backHref} className="text-gray-500 hover:text-gray-300 text-sm flex items-center gap-1 w-fit">
        {t.backToOverview}
      </Link>

      {data.isPartial && (
        <div className="bg-yellow-900/30 border border-yellow-700/50 rounded-lg px-4 py-2 text-yellow-300 text-xs">
          {t.scoringIncomplete}
        </div>
      )}

      {/* Match identity */}
      <div className="bg-gray-900 rounded-xl p-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h1 className="text-lg font-semibold text-white">
              {data.heroName ?? `Hero #${data.heroId}`}
            </h1>
            <p className="text-gray-400 text-sm mt-0.5">
              {t.positions[data.position] ?? `Position ${data.position}`} ·{" "}
              {data.durationMinutes}m · #{data.matchId}
            </p>
          </div>
          <span
            className={`flex-shrink-0 text-sm font-semibold px-3 py-1 rounded-full ${
              data.result === "win"
                ? "bg-green-900/50 text-green-400"
                : data.result === "loss"
                ? "bg-red-900/50 text-red-400"
                : "bg-gray-800 text-gray-500"
            }`}
          >
            {data.result === "win" ? t.victory : data.result === "loss" ? t.defeat : t.unknown}
          </span>
        </div>
      </div>

      {/* Overall scores */}
      <div className="bg-gray-900 rounded-xl p-4 flex flex-col gap-4">
        <div className="flex justify-around">
          <ScoreBadge
            score={
              data.overallPositionScore !== null && data.overallHeroScore !== null
                ? Math.round(((data.overallPositionScore + data.overallHeroScore) / 2) * 10) / 10
                : data.overallPositionScore ?? data.overallHeroScore
            }
            label={t.overall}
            size="lg"
          />
          <ScoreBadge score={data.overallPositionScore} label={t.roleLabel} />
          <ScoreBadge score={data.overallHeroScore}     label={t.heroLabel} />
        </div>

        {data.gameCloseness !== null && data.gameCloseness !== undefined && (
          <div className="flex justify-center">
            <span className="text-xs text-gray-500">
              {t.gameBalance}:{" "}
              <span className="text-gray-400">
                {data.gameCloseness >= 0.8
                  ? t.evenGame
                  : data.gameCloseness >= 0.5
                  ? t.moderatelyOneSided
                  : t.heavilyOneSided}
              </span>
              <span className="text-gray-600 ml-1">({(data.gameCloseness * 100).toFixed(0)}%)</span>
            </span>
          </div>
        )}

        {!data.hasBenchmarkContext && (
          <p className="text-gray-600 text-xs text-center border-t border-gray-800 pt-3">
            {t.benchmarkUnavailable}
          </p>
        )}

        {data.shortSummary && data.hasBenchmarkContext && (
          <p className="text-gray-400 text-sm text-center leading-snug border-t border-gray-800 pt-3">
            {data.shortSummary}
          </p>
        )}
      </div>

      {/* Phase breakdown */}
      <div className="flex flex-col gap-2">
        <h2 className="text-xs text-gray-500 uppercase tracking-wide">{t.phaseBreakdown}</h2>
        <PhaseBar
          early={data.phaseBreakdown.early_game}
          mid={data.phaseBreakdown.mid_game}
          late={data.phaseBreakdown.late_game}
          strongestPhase={data.strongestPhase}
          weakestPhase={data.weakestPhase}
        />
      </div>

      {/* Strengths & weaknesses */}
      {(data.topStrengths || data.topWeaknesses) && (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-gray-900 rounded-xl p-4">
            <h2 className="text-xs text-gray-500 uppercase tracking-wide mb-3">{t.strengths}</h2>
            {data.topStrengths && data.topStrengths.length > 0 ? (
              <ul className="flex flex-col gap-1.5">
                {data.topStrengths.map((s) => (
                  <li key={s} className="text-green-400 text-sm flex items-center gap-1.5">
                    <span className="text-green-600 text-xs">▲</span> {translateStat(s)}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-600 text-xs">{t.noneIdentified}</p>
            )}
          </div>
          <div className="bg-gray-900 rounded-xl p-4">
            <h2 className="text-xs text-gray-500 uppercase tracking-wide mb-3">{t.weaknesses}</h2>
            {data.topWeaknesses && data.topWeaknesses.length > 0 ? (
              <ul className="flex flex-col gap-1.5">
                {data.topWeaknesses.map((w) => (
                  <li key={w} className="text-red-400 text-sm flex items-center gap-1.5">
                    <span className="text-red-600 text-xs">▼</span> {translateStat(w)}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-600 text-xs">{t.noneIdentified}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-5 animate-pulse">
      <div className="h-4 w-28 bg-gray-800 rounded" />
      <div className="bg-gray-900 rounded-xl p-4 flex justify-between">
        <div className="flex flex-col gap-2">
          <div className="h-6 w-32 bg-gray-800 rounded" />
          <div className="h-4 w-48 bg-gray-800 rounded" />
        </div>
        <div className="h-7 w-16 bg-gray-800 rounded-full" />
      </div>
      <div className="bg-gray-900 rounded-xl p-6 flex justify-around">
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex flex-col items-center gap-2">
            <div className="h-8 w-14 bg-gray-800 rounded" />
            <div className="h-3 w-10 bg-gray-800 rounded" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-3">
        {[0, 1, 2].map((i) => <div key={i} className="bg-gray-800 rounded-lg h-24" />)}
      </div>
    </div>
  );
}

function ErrorState({ message, backLabel, onBack }: { message: string; backLabel: string; onBack: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center">
      <div className="bg-gray-900 rounded-xl p-6 max-w-sm w-full">
        <p className="text-red-400 text-sm mb-4">{message}</p>
        <button onClick={onBack} className="text-gray-400 hover:text-white text-sm underline">
          {backLabel}
        </button>
      </div>
    </div>
  );
}
