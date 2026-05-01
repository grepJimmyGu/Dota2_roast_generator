"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { MatchDetail, PhaseStatEntry, AnalysisEntry } from "@/lib/types";
import ScoreBadge from "@/components/ScoreBadge";
import PhaseBar from "@/components/PhaseBar";
import PercentileBar from "@/components/PercentileBar";
import { useLanguage } from "@/contexts/LanguageContext";
import { STAT_LABEL, Locale } from "@/lib/i18n";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const POSITION_LABELS: Record<number, string> = {
  1: "Carry", 2: "Mid", 3: "Offlane", 4: "Soft Support", 5: "Hard Support",
};

function SectionHeader({ label }: { label: string }) {
  return <h2 className="text-xs text-gray-500 uppercase tracking-wide">{label}</h2>;
}

function StatRow({ label, value }: { label: string; value: number | null }) {
  if (value === null || value === 0) return null;
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-gray-500">{label}</span>
      <span className="text-xs text-gray-300 tabular-nums">{value.toLocaleString()}</span>
    </div>
  );
}

function PhaseStatsCard({ stats, t }: { stats: PhaseStatEntry; t: ReturnType<typeof useLanguage>["t"] }) {
  return (
    <div className="flex flex-col gap-1 pt-2 border-t border-gray-700/50 mt-2">
      <StatRow label={t.statNetWorth}    value={stats.netWorth}    />
      <StatRow label={t.statHeroDamage}  value={stats.heroDamage}  />
      <StatRow label={t.statTowerDamage} value={stats.towerDamage} />
      <StatRow label={t.statLastHits}    value={stats.lastHits}    />
      <StatRow label={t.statKills}       value={stats.kills}       />
      <StatRow label={t.statDeaths}      value={stats.deaths}      />
    </div>
  );
}

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

  function translateStat(label: string): string {
    return STAT_LABEL[label]?.[locale as Locale] ?? label;
  }

  const overallScore =
    data.overallPositionScore !== null && data.overallHeroScore !== null
      ? Math.round(((data.overallPositionScore + data.overallHeroScore) / 2) * 10) / 10
      : data.overallPositionScore ?? data.overallHeroScore;

  const consistencyColor: Record<string, string> = {
    Consistent: "text-green-400", Variable: "text-yellow-400", Volatile: "text-red-400",
  };

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
              {POSITION_LABELS[data.position] ?? `Position ${data.position}`} · {data.durationMinutes}m · #{data.matchId}
            </p>
            {data.performanceProfile && (
              <span className="text-xs text-indigo-400 mt-1 inline-block">{data.performanceProfile}</span>
            )}
          </div>
          <span className={`flex-shrink-0 text-sm font-semibold px-3 py-1 rounded-full ${
            data.result === "win" ? "bg-green-900/50 text-green-400"
            : data.result === "loss" ? "bg-red-900/50 text-red-400"
            : "bg-gray-800 text-gray-500"
          }`}>
            {data.result === "win" ? t.victory : data.result === "loss" ? t.defeat : t.unknown}
          </span>
        </div>
      </div>

      {/* Bucket 1: Performance */}
      <div className="flex flex-col gap-3">
        <SectionHeader label={t.sectionPerformance} />
        <div className="bg-gray-900 rounded-xl p-4 flex flex-col gap-4">
          <div className="flex justify-around">
            <ScoreBadge score={overallScore} label={t.overall} size="lg" />
            <ScoreBadge score={data.overallPositionScore} label={t.roleLabel} />
            <ScoreBadge score={data.overallHeroScore}     label={t.heroLabel} />
          </div>

          {/* Percentile bars */}
          {data.scoreContext && (
            <div className="flex flex-col gap-3 border-t border-gray-800 pt-3">
              <PercentileBar ctx={data.scoreContext} label={`${t.roleLabel} — ${t.benchmarkRoleExplain}`} />
              {data.heroScoreContext && (
                <PercentileBar ctx={data.heroScoreContext} label={`${t.heroLabel} — ${t.benchmarkHeroExplain}`} />
              )}
              <p className="text-gray-700 text-xs">{t.heuristicNote}</p>
            </div>
          )}

          {data.gameCloseness !== null && data.gameCloseness !== undefined && (
            <div className="flex justify-center">
              <span className="text-xs text-gray-500">
                {t.gameBalance}:{" "}
                <span className="text-gray-400">
                  {data.gameCloseness >= 0.8 ? t.evenGame
                    : data.gameCloseness >= 0.5 ? t.moderatelyOneSided
                    : t.heavilyOneSided}
                </span>
              </span>
            </div>
          )}

          {!data.hasBenchmarkContext && (
            <p className="text-gray-600 text-xs text-center">{t.benchmarkUnavailable}</p>
          )}

          {data.matchNarrative && data.hasBenchmarkContext && (
            <p className="text-gray-300 text-sm leading-relaxed border-t border-gray-800 pt-3">
              {data.matchNarrative}
            </p>
          )}
        </div>
      </div>

      {/* Phase Breakdown */}
      <div className="flex flex-col gap-3">
        <SectionHeader label={t.phaseBreakdown} />
        <PhaseBar
          early={data.phaseBreakdown.early_game}
          mid={data.phaseBreakdown.mid_game}
          late={data.phaseBreakdown.late_game}
          strongestPhase={data.strongestPhase}
          weakestPhase={data.weakestPhase}
          phaseNarrative={data.phaseNarrative}
          phaseStats={data.phaseStats}
        />
      </div>

      {/* Bucket 2: What Went Well */}
      {(data.matchAnalysis?.wentWell?.length || data.topStrengths?.length) && (
        <div className="flex flex-col gap-3">
          <SectionHeader label={t.sectionWentWell} />
          <div className="flex flex-col gap-3">
            {(data.matchAnalysis?.wentWell ?? []).map((entry, i) => (
              <AnalysisCard key={i} entry={entry} accent="green" t={t} />
            ))}
            {!data.matchAnalysis?.wentWell?.length && data.topStrengths?.length && (
              <div className="bg-gray-900 rounded-xl p-4">
                <ul className="flex flex-col gap-1.5">
                  {data.topStrengths.map((s) => (
                    <li key={s} className="text-green-400 text-sm flex items-center gap-1.5">
                      <span className="text-green-600 text-xs">▲</span> {translateStat(s)}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Bucket 3: What Hurt Most */}
      {(data.matchAnalysis?.hurtMost?.length || data.topWeaknesses?.length) && (
        <div className="flex flex-col gap-3">
          <SectionHeader label={t.sectionHurtMost} />
          <div className="flex flex-col gap-3">
            {(data.matchAnalysis?.hurtMost ?? []).map((entry, i) => (
              <AnalysisCard key={i} entry={entry} accent="red" t={t} />
            ))}
            {!data.matchAnalysis?.hurtMost?.length && data.topWeaknesses?.length && (
              <div className="bg-gray-900 rounded-xl p-4">
                <ul className="flex flex-col gap-1.5">
                  {data.topWeaknesses.map((w) => (
                    <li key={w} className="text-red-400 text-sm flex items-center gap-1.5">
                      <span className="text-red-600 text-xs">▼</span> {translateStat(w)}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Bucket 4: What to Work On */}
      {(data.matchAnalysis?.workOn?.length || data.improvementSuggestion) && (
        <div className="flex flex-col gap-3">
          <SectionHeader label={t.sectionWorkOn} />
          <div className="flex flex-col gap-3">
            {(data.matchAnalysis?.workOn ?? []).map((entry, i) => (
              <AnalysisCard key={i} entry={entry} accent="indigo" t={t} />
            ))}
            {!data.matchAnalysis?.workOn?.length && data.improvementSuggestion && (
              <div className="bg-gray-900 rounded-xl p-4">
                <p className="text-indigo-300 text-sm leading-relaxed">{data.improvementSuggestion}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function AnalysisCard({
  entry, accent, t,
}: {
  entry: AnalysisEntry;
  accent: "green" | "red" | "indigo";
  t: ReturnType<typeof useLanguage>["t"];
}) {
  const border = { green: "border-green-800/30", red: "border-red-800/30", indigo: "border-indigo-800/30" }[accent];
  const titleColor = { green: "text-green-400", red: "text-red-400", indigo: "text-indigo-400" }[accent];

  return (
    <div className={`bg-gray-900 rounded-xl p-4 border ${border} flex flex-col gap-2`}>
      <div className="flex items-center justify-between gap-2">
        <span className={`text-sm font-medium ${titleColor}`}>{entry.title}</span>
        {entry.phase && (
          <span className="text-xs text-gray-600 flex-shrink-0 capitalize">{entry.phase}</span>
        )}
      </div>
      <p className="text-gray-300 text-sm leading-relaxed">{entry.detail}</p>
      <div className="flex flex-col gap-1 pt-1 border-t border-gray-800">
        <p className="text-xs text-gray-500">
          <span className="text-gray-600">{t.whyItMatters}: </span>{entry.whyItMatters}
        </p>
        <p className="text-xs text-gray-500">
          <span className="text-gray-600">{t.takeaway}: </span>
          <span className={titleColor}>{entry.takeaway}</span>
        </p>
      </div>
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
        {[0,1,2].map((i) => (
          <div key={i} className="flex flex-col items-center gap-2">
            <div className="h-8 w-14 bg-gray-800 rounded" />
            <div className="h-3 w-10 bg-gray-800 rounded" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-3">
        {[0,1,2].map((i) => <div key={i} className="bg-gray-800 rounded-lg h-28" />)}
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
