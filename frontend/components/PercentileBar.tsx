"use client";

import { ScoreContext } from "@/lib/types";

interface Props {
  ctx: ScoreContext;
  label?: string;
  benchmarkLabelOverride?: string;
}

function barColor(percentile: number): string {
  if (percentile >= 70) return "bg-green-500";
  if (percentile >= 40) return "bg-yellow-500";
  return "bg-red-500";
}

export default function PercentileBar({ ctx, label, benchmarkLabelOverride }: Props) {
  const pct   = Math.min(100, Math.max(0, ctx.percentile));
  const color = barColor(pct);
  const bracketInfo = ctx.bracketLabel ? `${ctx.bracketLabel}` : null;

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        {label && <span className="text-xs text-gray-500">{label}</span>}
        <div className="flex items-center gap-2 ml-auto">
          {bracketInfo && (
            <span className="text-xs text-gray-600 border border-gray-700 rounded px-1.5 py-0.5">
              {bracketInfo}
            </span>
          )}
          <span className="text-xs text-gray-400 font-medium">
            {ctx.label} · {pct.toFixed(0)}th pct
          </span>
        </div>
      </div>

      {/* Bar */}
      <div className="relative h-2 bg-gray-800 rounded-full overflow-visible">
        <div
          className={`absolute left-0 top-0 h-full rounded-full ${color} transition-all`}
          style={{ width: `${pct}%` }}
        />
        {/* Average tick at 50% */}
        <div
          className="absolute top-[-2px] h-[calc(100%+4px)] w-0.5 bg-gray-500 rounded"
          style={{ left: "50%" }}
        />
      </div>

      {/* Scale labels */}
      <div className="flex justify-between text-xs text-gray-700">
        <span>0</span>
        <span>{benchmarkLabelOverride ?? `avg ${ctx.benchmarkAvg}`}</span>
        <span>100</span>
      </div>
    </div>
  );
}
