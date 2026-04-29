interface Props {
  score: number | null;
  label?: string;
  size?: "sm" | "lg";
}

function scoreColor(score: number | null): string {
  if (score === null) return "text-gray-500";
  if (score >= 65) return "text-green-400";
  if (score >= 50) return "text-yellow-400";
  if (score >= 35) return "text-orange-400";
  return "text-red-400";
}

export default function ScoreBadge({ score, label, size = "sm" }: Props) {
  const color = scoreColor(score);
  const numSize = size === "lg" ? "text-4xl font-bold" : "text-xl font-semibold";

  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className={`${numSize} ${color} tabular-nums`}>
        {score !== null ? score.toFixed(1) : "—"}
      </span>
      {label && <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>}
    </div>
  );
}
