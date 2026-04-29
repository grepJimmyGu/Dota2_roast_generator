import type { Metadata } from "next";
import "./globals.css";
import { LanguageProvider } from "@/contexts/LanguageContext";
import LanguageToggle from "@/components/LanguageToggle";

export const metadata: Metadata = {
  title: "Dota 2 MMR Analyzer",
  description: "Per-match, per-phase performance scoring",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <LanguageProvider>
          <div className="max-w-2xl mx-auto px-4">
            <div className="flex justify-end pt-4 pb-0">
              <LanguageToggle />
            </div>
            <div className="py-4">{children}</div>
          </div>
        </LanguageProvider>
      </body>
    </html>
  );
}
