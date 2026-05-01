"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { PlayerOverview } from "@/lib/types";
import ScoreBadge from "@/components/ScoreBadge";
import MatchCard from "@/components/MatchCard";
import { loadProfile, saveProfile } from "@/lib/profile";
import { useLanguage } from "@/contexts/LanguageContext";
import RoastCard from "@/components/RoastCard";
import PercentileBar from "@/components/PercentileBar";
import RecurringPatternCard from "@/components/RecurringPatternCard";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function SectionHeader({ label }: { label: string }) {
  return <h2 className="text-xs text-gray-500 uppercase tracking-wide">{label}</h2>;
}

export default function PlayerOverviewPage() {
  const { steamId } = useParams<{ steamId: string }>();
  const router = useRouter();
  const { t, locale } = useLanguage();

  const [data, setData]             = useState<PlayerOverview | null>(null);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string | null>(null);
  const [isSaved, setIsSaved]       = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!steamId) return;
    const profile = loadProfile();
    setIsSaved(profile?.steamId === parseInt(steamId, 10));
  }, [steamId]);

  useEffect(() => {
    if (!steamId) return;
    setLoading(true);
    setError(null);
    fetch(`${API}/players/${steamId}/overview?lang=${locale}`)
      .then(async (res) => {
        if (res.status === 404) throw new Error("Player not found on Stratz.");
        if (!res.ok) throw new Error(`Server error (${res.status}). Try again later.`);
        return res.json();
      })
      .then((json) => { setData(json); setLoading(false); })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, [steamId, locale]);

  if (loading) return <LoadingSkeleton hint={t.firstLoadHint} />;
  if (error)   return <ErrorState message={error} backLabel={t.backToSearchLink} onBack={() => router.push("/")} />;
  if (!data)   return null;

  const noMatches  = data.recentMatchCount === 0;
  const steamIdNum = parseInt(steamId, 10);

  const trendMap: Record<string, string> = {
    improving: t.improving, declining: t.declining, stable: t.stable,
  };
  const trendColor: Record<string, string> = {
    improving: "text-green-400", declining: "text-red-400", stable: "text-yellow-400",
  };
  const consistencyColor: Record<string, string> = {
    Consistent: "text-green-400", Variable: "text-yellow-400", Volatile: "text-red-400",
  };
  const consistencyLabel: Record<string, string> = {
    Consistent: t.consistentRating, Variable: t.variableRating, Volatile: t.volatileRating,
  };

  return (
    <div className="flex flex-col gap-5">
      <Link href="/" className="text-gray-500 hover:text-gray-300 text-sm flex items-center gap-1 w-fit">
        {t.backToSearch}
      </Link>

      {/* Stale banner */}
      {data.isStale && (
        <div className="bg-yellow-900/30 border border-yellow-700/50 rounded-lg px-4 py-2 text-yellow-300 text-xs flex items-center justify-between gap-3">
          <span>
            {t.dataStale}
            {data.lastRefreshedAt && (
              <span className="text-yellow-500 ml-1">
                — {t.lastUpdated} {new Date(data.lastRefreshedAt).toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
          </span>
          <button
            disabled={refreshing}
            className="underline hover:text-yellow-200 disabled:opacity-50 flex-shrink-0"
            onClick={async () => {
              setRefreshing(true);
              try {
                await fetch(`${API}/players/${steamId}/refresh`, { method: "POST" });
                window.location.reload();
              } finally { setRefreshing(false); }
            }}
          >
            {refreshing ? t.refreshing : t.refreshNow}
          </button>
        </div>
      )}

      {data.dataCompleteness && data.dataCompleteness.failedMatchCount > 0 && (
        <div className="bg-gray-800/60 border border-gray-700 rounded-lg px-4 py-2 text-gray-400 text-xs">
          {t.partialData(data.dataCompleteness.failedMatchCount)}
        </div>
      )}

      {/* Player identity */}
      <div className="bg-gray-900 rounded-xl p-4 flex items-center gap-4">
        {data.avatarUrl && (
          <img src={data.avatarUrl} alt="avatar" className="w-14 h-14 rounded-full object-cover flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-semibold text-white truncate">
            {data.playerName ?? `Steam #${steamId}`}
          </h1>
          <p className="text-gray-500 text-xs mt-0.5">
            {t.rankedMatches(data.recentMatchCount)}
            {data.rank ? ` · ${t.rank} ${data.rank}` : ""}
          </p>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            {data.performanceArchetype && (
              <span className="text-xs text-indigo-400">{data.performanceArchetype}</span>
            )}
            {data.recentTrend && (
              <span className={`text-xs ${trendColor[data.recentTrend] ?? "text-gray-400"}`}>
                {trendMap[data.recentTrend] ?? data.recentTrend}
              </span>
            )}
          </div>
        </div>
        <button
          onClick={() => {
            if (isSaved) return;
            saveProfile({ steamId: steamIdNum, playerName: data.playerName, avatarUrl: data.avatarUrl });
            setIsSaved(true);
          }}
          disabled={isSaved}
          className={`flex-shrink-0 text-xs px-3 py-1.5 rounded-lg border transition-colors ${
            isSaved
              ? "border-green-700 text-green-500 cursor-default"
              : "border-gray-700 text-gray-400 hover:border-indigo-500 hover:text-indigo-400"
          }`}
        >
          {isSaved ? t.saved : t.saveProfile}
        </button>
      </div>

      {noMatches ? (
        <EmptyState noMatches={t.noMatches} hint={t.noMatchesHint} />
      ) : (
        <>
          {/* Bucket 1: Current Form */}
          <div className="flex flex-col gap-3">
            <SectionHeader label={t.sectionCurrentForm} />
            <div className="bg-gray-900 rounded-xl p-4 flex flex-col gap-4">
              <div className="flex justify-around">
                <ScoreBadge score={data.averageOverallScore}  label={t.overall}  size="lg" />
                <ScoreBadge score={data.averagePositionScore} label={t.roleAvg} />
                <ScoreBadge score={data.averageHeroScore}     label={t.heroAvg} />
              </div>

              <div className="flex gap-4 justify-center text-xs flex-wrap">
                {data.consistencyRating && (
                  <span className={consistencyColor[data.consistencyRating] ?? "text-gray-400"}>
                    {t.consistencyLabel}: <span className="font-medium">{consistencyLabel[data.consistencyRating] ?? data.consistencyRating}</span>
                  </span>
                )}
                {data.strongestPhase && (
                  <span className="text-green-400">
                    ▲ {t.strongest}: <span className="font-medium capitalize">{data.strongestPhase}</span>
                  </span>
                )}
                {data.weakestPhase && (
                  <span className="text-red-400">
                    ▼ {t.weakest}: <span className="font-medium capitalize">{data.weakestPhase}</span>
                  </span>
                )}
              </div>

              {/* Percentile bar */}
              {data.scoreContext && (
                <div className="border-t border-gray-800 pt-3">
                  <PercentileBar ctx={data.scoreContext} label={t.roleAvg} />
                </div>
              )}

              {data.playerNarrative && (
                <p className="text-gray-400 text-sm leading-relaxed border-t border-gray-800 pt-3">
                  {data.playerNarrative}
                </p>
              )}
            </div>
          </div>

          {/* AI Roast */}
          <RoastCard steamId={steamIdNum} />

          {/* Bucket 2: Strength Profile */}
          {(data.recurringPatterns?.some(p => p.isStrength) || data.bestHeroes?.length) && (
            <div className="flex flex-col gap-3">
              <SectionHeader label={t.sectionStrengthProfile} />
              {data.recurringPatterns?.filter(p => p.isStrength).map((pattern, i) => (
                <RecurringPatternCard key={i} pattern={pattern} steamId={steamIdNum} />
              ))}
              {data.bestHeroes && data.bestHeroes.length > 0 && (
                <div className="bg-gray-900 rounded-xl p-4">
                  <p className="text-xs text-gray-500 mb-2">{t.bestHeroes}</p>
                  <div className="flex flex-col gap-2">
                    {data.bestHeroes.map((h) => (
                      <div key={h.heroId} className="flex items-center justify-between">
                        <span className="text-sm text-white">{h.heroName}</span>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-gray-500">{h.games}g</span>
                          <span className="text-sm font-medium text-yellow-400 tabular-nums">
                            {h.avgScore.toFixed(1)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Bucket 3: Recurring Issues */}
          {data.recurringPatterns?.some(p => !p.isStrength) && (
            <div className="flex flex-col gap-3">
              <SectionHeader label={t.sectionRecurringIssues} />
              {data.recurringPatterns.filter(p => !p.isStrength).map((pattern, i) => (
                <RecurringPatternCard key={i} pattern={pattern} steamId={steamIdNum} />
              ))}
            </div>
          )}

          {/* Bucket 4: Recent Matches */}
          <div className="flex flex-col gap-2">
            <SectionHeader label={t.recentMatches} />
            {data.recentMatches.map((m) => (
              <MatchCard key={m.matchId} match={m} steamId={steamIdNum} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function LoadingSkeleton({ hint }: { hint: string }) {
  return (
    <div className="flex flex-col gap-5">
      <div className="h-4 w-16 bg-gray-800 rounded animate-pulse" />
      <div className="bg-gray-900/60 border border-gray-800 rounded-lg px-4 py-2 text-gray-500 text-xs">{hint}</div>
      <div className="flex flex-col gap-5 animate-pulse">
        <div className="bg-gray-900 rounded-xl p-4 flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-gray-800" />
          <div className="flex-1 flex flex-col gap-2">
            <div className="h-5 w-32 bg-gray-800 rounded" />
            <div className="h-3 w-24 bg-gray-800 rounded" />
          </div>
        </div>
        <div className="bg-gray-900 rounded-xl p-6 flex justify-around">
          {[0,1,2].map((i) => (
            <div key={i} className="flex flex-col items-center gap-2">
              <div className="h-8 w-14 bg-gray-800 rounded" />
              <div className="h-3 w-10 bg-gray-800 rounded" />
            </div>
          ))}
        </div>
        {[0,1,2,3,4].map((i) => <div key={i} className="bg-gray-800 rounded-lg h-14" />)}
      </div>
    </div>
  );
}

function ErrorState({ message, backLabel, onBack }: { message: string; backLabel: string; onBack: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center">
      <div className="bg-gray-900 rounded-xl p-6 max-w-sm w-full">
        <p className="text-red-400 text-sm mb-4">{message}</p>
        <button onClick={onBack} className="text-gray-400 hover:text-white text-sm underline">{backLabel}</button>
      </div>
    </div>
  );
}

function EmptyState({ noMatches, hint }: { noMatches: string; hint: string }) {
  return (
    <div className="bg-gray-900 rounded-xl p-6 text-center">
      <p className="text-gray-400 text-sm">{noMatches}</p>
      <p className="text-gray-600 text-xs mt-1">{hint}</p>
    </div>
  );
}
