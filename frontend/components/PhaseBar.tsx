"use client";

import ScoreBadge from "./ScoreBadge";
import { useLanguage } from "@/contexts/LanguageContext";

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
}

export default function PhaseBar({ early, mid, late, strongestPhase, weakestPhase }: Props) {
  const { t } = useLanguage();

  const phases = [
    { key: "lane phase", label: t.lanePhase, phase: "early" as const },
    { key: "mid game",   label: t.midGame,   phase: "mid"   as const },
    { key: "closing",    label: t.lateGame,  phase: "late"  as const },
  ];
  const data = { early, mid, late };

  return (
    <div className="grid grid-cols-3 gap-3">
      {phases.map(({ key, label, phase }) => {
        const scores     = data[phase];
        const isStrongest = strongestPhase === key;
        const isWeakest   = weakestPhase   === key;
        const ring = isStrongest
          ? "ring-1 ring-green-500/50"
          : isWeakest
          ? "ring-1 ring-red-500/30"
          : "";

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
          </div>
        );
      })}
    </div>
  );
}
