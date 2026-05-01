"use client";

import { useLanguage } from "@/contexts/LanguageContext";
import { ScoreContext } from "@/lib/types";

interface Props {
  ctx: ScoreContext;
  label?: string;
}

function barColor(percentile: number): string {
  if (percentile >= 70) return "bg-green-500";
  if (percentile >= 40) return "bg-yellow-500";
  return "bg-red-500";
}

export default function PercentileBar({ ctx, label }: Props) {
  const { t } = useLanguage();
  const pct    = Math.min(100, Math.max(0, ctx.percentile));
  const color  = barColor(pct);

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">{label}</span>
          <span className="text-xs text-gray-400">
            {ctx.label} · <span className="tabular-nums">{pct.toFixed(0)}th {t.percentileOf}</span>
          </span>
        </div>
      )}

      {/* Bar */}
      <div className="relative h-2 bg-gray-800 rounded-full overflow-visible">
        {/* Filled portion */}
        <div
          className={`absolute left-0 top-0 h-full rounded-full ${color} transition-all`}
          style={{ width: `${pct}%` }}
        />
        {/* Average tick at 50% */}
        <div
          className="absolute top-[-2px] h-[calc(100%+4px)] w-0.5 bg-gray-500 rounded"
          style={{ left: "50%" }}
          title={`${t.benchmarkAvgLabel} 50`}
        />
      </div>

      {/* Labels */}
      <div className="flex justify-between text-xs text-gray-600">
        <span>0</span>
        <span>{t.benchmarkAvgLabel} {ctx.benchmarkAvg}</span>
        <span>100</span>
      </div>
    </div>
  );
}
