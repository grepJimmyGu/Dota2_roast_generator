"use client";

import { useState, useCallback } from "react";
import { useLanguage } from "@/contexts/LanguageContext";

interface CritiqueResponse {
  title: string;
  primary_role: string;
  overall_verdict: string;
  critique: string;
  key_problem_tags: string[];
  evidence_used: { match_id: string; reason: string }[];
  final_punchline: string;
  tone: "light" | "medium" | "high";
}

interface Props {
  steamId: number;
}

const TONE_STYLE: Record<string, string> = {
  light:  "border-yellow-700/40 bg-yellow-950/20",
  medium: "border-orange-700/50 bg-orange-950/25",
  high:   "border-red-700/50    bg-red-950/25",
};

const TONE_LABEL: Record<string, { en: string; zh: string }> = {
  light:  { en: "Light roast",   zh: "轻度开烤" },
  medium: { en: "Medium roast",  zh: "中度开烤" },
  high:   { en: "Well done",     zh: "烤熟了" },
};

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function RoastCard({ steamId }: Props) {
  const { locale } = useLanguage();
  const [data, setData]         = useState<CritiqueResponse | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [copied, setCopied]     = useState(false);

  const copyToClipboard = useCallback(async (d: CritiqueResponse) => {
    const text = [
      `【${d.title}】`,
      `"${d.overall_verdict}"`,
      "",
      d.critique,
      "",
      `💀 ${d.final_punchline}`,
      "",
      d.key_problem_tags.length ? `标签：${d.key_problem_tags.join(" · ")}` : "",
      "—— Dota 2 AI 战绩点评",
    ].filter(Boolean).join("\n");

    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  const label = locale === "zh"
    ? { btn: "🔥 开烤", loading: "AI 正在分析你的近10场比赛…", retry: "再烤一次", err: "生成失败，请重试。" }
    : { btn: "🔥 Roast Me", loading: "AI is reading your last 10 matches…", retry: "Roast again", err: "Generation failed. Try again." };

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/players/${steamId}/roast?lang=zh`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || label.err);
      }
      setData(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : label.err);
    } finally {
      setLoading(false);
    }
  }

  // Initial state — big invite button
  if (!data && !loading && !error) {
    return (
      <div className="border border-dashed border-orange-700/40 rounded-xl p-6 flex flex-col items-center gap-3 text-center">
        <p className="text-gray-500 text-xs uppercase tracking-wide">
          {locale === "zh" ? "AI 战绩点评" : "AI Performance Roast"}
        </p>
        <p className="text-gray-400 text-sm">
          {locale === "zh"
            ? "基于你近10场比赛数据，AI 将给出一份毒舌战绩点评。"
            : "Based on your last 10 matches, AI will write a data-grounded performance critique."}
        </p>
        <button
          onClick={generate}
          className="mt-1 bg-orange-700 hover:bg-orange-600 text-white font-semibold px-5 py-2.5 rounded-lg text-sm transition-colors"
        >
          {label.btn}
        </button>
        <p className="text-gray-700 text-xs">
          {locale === "zh" ? "生成约需10-20秒" : "Takes ~10-20 seconds"}
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="border border-orange-700/30 rounded-xl p-6 flex flex-col items-center gap-3 text-center animate-pulse">
        <div className="w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-orange-400 text-sm">{label.loading}</p>
        <p className="text-gray-600 text-xs">
          {locale === "zh" ? "这很刺激，请稍候…" : "This might sting a little…"}
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="border border-red-900/40 rounded-xl p-5 flex flex-col gap-3">
        <p className="text-red-400 text-sm">{error}</p>
        <button onClick={generate} className="text-gray-400 hover:text-white text-sm underline w-fit">
          {label.retry}
        </button>
      </div>
    );
  }

  if (!data) return null;

  const toneStyle = TONE_STYLE[data.tone] ?? TONE_STYLE.medium;
  const toneLabel = TONE_LABEL[data.tone]?.[locale] ?? data.tone;

  return (
    <div className={`border rounded-xl p-5 flex flex-col gap-4 ${toneStyle}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="text-xs text-orange-400 uppercase tracking-wide font-medium">
            {locale === "zh" ? "AI 战绩点评" : "AI Performance Roast"} · {toneLabel}
          </span>
          <h2 className="text-white font-bold text-lg mt-0.5">{data.title}</h2>
        </div>
        <button
          onClick={() => { setData(null); setError(null); }}
          className="text-gray-600 hover:text-gray-400 text-xs flex-shrink-0 mt-1"
        >
          ✕
        </button>
      </div>

      {/* Verdict */}
      <p className="text-orange-300 text-sm font-medium italic">"{data.overall_verdict}"</p>

      {/* Problem tags */}
      {data.key_problem_tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {data.key_problem_tags.map((tag) => (
            <span
              key={tag}
              className="text-xs bg-red-900/40 text-red-300 border border-red-800/40 px-2 py-0.5 rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Critique body */}
      <div className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
        {data.critique}
      </div>

      {/* Punchline */}
      <div className="border-t border-orange-800/30 pt-3">
        <p className="text-orange-400 text-sm font-semibold text-center">
          💀 {data.final_punchline}
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-center gap-4">
        <button
          onClick={() => copyToClipboard(data)}
          className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-colors ${
            copied
              ? "border-green-700 text-green-400 bg-green-950/30"
              : "border-gray-700 text-gray-400 hover:border-orange-600 hover:text-orange-400"
          }`}
        >
          {copied ? "✓ 已复制" : "复制全文"}
        </button>
        <button
          onClick={generate}
          disabled={loading}
          className="text-gray-600 hover:text-gray-400 text-xs underline disabled:opacity-50"
        >
          {label.retry}
        </button>
      </div>
    </div>
  );
}
