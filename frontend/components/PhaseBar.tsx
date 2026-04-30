"use client";

import ScoreBadge from "./ScoreBadge";
import { useLanguage } from "@/contexts/LanguageContext";
import { PhaseStatEntry } from "@/lib/types";

interface PhaseScore {
  positionScore: number | null;
  heroScore: number | null;
}

interface Props {
  early: PhaseScore;
  mid: PhaseScore;
  late: PhaseScore;
  strongestPhase?: string | null;
  weakestPhase?: string | null;
  phaseNarrative?: { early_game?: string; mid_game?: string; late_game?: string } | null;
  phaseStats?: { early_game?: PhaseStatEntry; mid_game?: PhaseStatEntry; late_game?: PhaseStatEntry } | null;
}

function StatLine({ label, value }: { label: string; value: number }) {
  if (!value) return null;
  return (
    <div className="flex justify-between text-xs">
      <span className="text-gray-600">{label}</span>
      <span className="text-gray-400 tabular-nums">{value.toLocaleString()}</span>
    </div>
  );
}

export default function PhaseBar({ early, mid, late, strongestPhase, weakestPhase, phaseNarrative, phaseStats }: Props) {
  const { t } = useLanguage();

  const phases = [
    { key: "lane phase", label: t.lanePhase, phase: "early" as const, phaseKey: "early_game" },
    { key: "mid game",   label: t.midGame,   phase: "mid"   as const, phaseKey: "mid_game"   },
    { key: "closing",    label: t.lateGame,  phase: "late"  as const, phaseKey: "late_game"  },
  ];
  const data = { early, mid, late };

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-3 gap-3">
        {phases.map(({ key, label, phase, phaseKey }) => {
          const scores      = data[phase];
          const isStrongest = strongestPhase === key;
          const isWeakest   = weakestPhase   === key;
          const narrative   = phaseNarrative?.[phaseKey as keyof typeof phaseNarrative];
          const stats       = phaseStats?.[phaseKey as keyof typeof phaseStats];
          const ring = isStrongest ? "ring-1 ring-green-500/50" : isWeakest ? "ring-1 ring-red-500/30" : "";

          return (
            <div key={phase} className={`bg-gray-800 rounded-lg p-3 flex flex-col gap-2 ${ring}`}>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">{label}</span>
                {isStrongest && <span className="text-xs text-green-400">{t.best}</span>}
                {isWeakest   && <span className="text-xs text-red-400">{t.weak}</span>}
              </div>
              <div className="flex justify-around">
                <ScoreBadge score={scores.positionScore} label={t.roleLabel} />
                <ScoreBadge score={scores.heroScore}     label={t.heroLabel} />
              </div>
              {stats && (
                <div className="flex flex-col gap-0.5 pt-1.5 border-t border-gray-700/50">
                  <StatLine label={t.statNetWorth}    value={stats.netWorth}    />
                  <StatLine label={t.statHeroDamage}  value={stats.heroDamage}  />
                  <StatLine label={t.statTowerDamage} value={stats.towerDamage} />
                  <StatLine label={t.statLastHits}    value={stats.lastHits}    />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Phase narratives below the grid */}
      {phaseNarrative && (
        <div className="flex flex-col gap-1.5">
          {phases.map(({ label, phaseKey }) => {
            const narrative = phaseNarrative?.[phaseKey as keyof typeof phaseNarrative];
            if (!narrative) return null;
            return (
              <p key={phaseKey} className="text-xs text-gray-500 leading-snug">
                <span className="text-gray-600">{label}: </span>{narrative}
              </p>
            );
          })}
        </div>
      )}
    </div>
  );
}
