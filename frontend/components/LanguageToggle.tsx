"use client";

import { useLanguage } from "@/contexts/LanguageContext";

export default function LanguageToggle() {
  const { locale, toggle } = useLanguage();

  return (
    <button
      onClick={toggle}
      className="text-xs text-gray-500 hover:text-gray-300 border border-gray-800 hover:border-gray-600 rounded-md px-2.5 py-1 transition-colors"
      title={locale === "en" ? "切换为中文" : "Switch to English"}
    >
      {locale === "en" ? "中文" : "EN"}
    </button>
  );
}
