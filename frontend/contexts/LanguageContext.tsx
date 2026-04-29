"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { Locale, Translation, translations } from "@/lib/i18n";

interface LanguageContextValue {
  locale: Locale;
  toggle: () => void;
  t: Translation;
}

const LanguageContext = createContext<LanguageContextValue>({
  locale: "en",
  toggle: () => {},
  t: translations["en"],
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>("en");

  useEffect(() => {
    const saved = localStorage.getItem("dota_locale") as Locale | null;
    if (saved === "en" || saved === "zh") setLocale(saved);
  }, []);

  function toggle() {
    setLocale((prev) => {
      const next: Locale = prev === "en" ? "zh" : "en";
      localStorage.setItem("dota_locale", next);
      return next;
    });
  }

  return (
    <LanguageContext.Provider value={{ locale, toggle, t: translations[locale] }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
