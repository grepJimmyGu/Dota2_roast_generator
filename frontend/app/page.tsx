"use client";

import { useState, FormEvent, useEffect } from "react";
import { useRouter } from "next/navigation";
import { parseSteamInput } from "@/lib/parseSteam";
import { loadProfile, clearProfile, SavedProfile } from "@/lib/profile";
import { useLanguage } from "@/contexts/LanguageContext";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface SearchResult {
  steamId: number;
  playerName: string | null;
  avatarUrl: string | null;
}

export default function LandingPage() {
  const router = useRouter();
  const { t } = useLanguage();

  const [myProfile, setMyProfile] = useState<SavedProfile | null>(null);
  useEffect(() => { setMyProfile(loadProfile()); }, []);

  const [idInput, setIdInput]   = useState("");
  const [idError, setIdError]   = useState<string | null>(null);

  function handleIdSubmit(e: FormEvent) {
    e.preventDefault();
    const { steamId, error } = parseSteamInput(idInput);
    if (error || !steamId) { setIdError(error ?? t.invalidInput); return; }
    setIdError(null);
    router.push(`/players/${steamId}`);
  }

  const [nameQuery, setNameQuery]           = useState("");
  const [searching, setSearching]           = useState(false);
  const [searchResults, setSearchResults]   = useState<SearchResult[] | null>(null);
  const [searchError, setSearchError]       = useState<string | null>(null);

  async function handleNameSearch(e: FormEvent) {
    e.preventDefault();
    const q = nameQuery.trim();
    if (q.length < 2) { setSearchError(t.enterAtLeast2); return; }
    setSearchError(null);
    setSearching(true);
    setSearchResults(null);
    try {
      const res = await fetch(`${API}/players/search?q=${encodeURIComponent(q)}`);
      if (!res.ok) throw new Error();
      const data: SearchResult[] = await res.json();
      setSearchResults(data);
      if (data.length === 0) setSearchError(t.noPlayersFound);
    } catch {
      setSearchError(t.searchUnavailable);
    } finally {
      setSearching(false);
    }
  }

  const [matchId, setMatchId]           = useState("");
  const [matchSteamId, setMatchSteamId] = useState("");
  const [matchError, setMatchError]     = useState<string | null>(null);

  function handleMatchSubmit(e: FormEvent) {
    e.preventDefault();
    const mid = matchId.trim();
    if (!mid || !/^\d+$/.test(mid)) { setMatchError(t.invalidMatchId); return; }
    const { steamId, error } = parseSteamInput(matchSteamId);
    if (error || !steamId) { setMatchError(error ?? t.invalidSteamId); return; }
    setMatchError(null);
    router.push(`/matches/${mid}?steamId=${steamId}`);
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] gap-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-white">{t.appTitle}</h1>
        <p className="mt-2 text-gray-400 text-sm">{t.appSubtitle}</p>
      </div>

      {/* My Profile */}
      {myProfile && (
        <div className="w-full max-w-sm bg-gray-900 rounded-xl p-4 flex items-center gap-3">
          {myProfile.avatarUrl && (
            <img src={myProfile.avatarUrl} className="w-10 h-10 rounded-full object-cover flex-shrink-0" alt="" />
          )}
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{t.myProfile}</p>
            <p className="text-sm font-medium text-white truncate">
              {myProfile.playerName ?? `Steam #${myProfile.steamId}`}
            </p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <button
              onClick={() => router.push(`/players/${myProfile.steamId}`)}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
            >
              {t.analyzePlayer}
            </button>
            <button
              onClick={() => { clearProfile(); setMyProfile(null); }}
              className="text-gray-600 hover:text-gray-400 text-xs px-2 py-1.5 rounded-lg transition-colors"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Search by name */}
      <div className="w-full max-w-sm flex flex-col gap-3">
        <p className="text-xs text-gray-500 uppercase tracking-wide">{t.searchByName}</p>
        <form onSubmit={handleNameSearch} className="flex gap-2">
          <input
            type="text"
            value={nameQuery}
            onChange={(e) => { setNameQuery(e.target.value); setSearchError(null); setSearchResults(null); }}
            placeholder={t.namePlaceholder}
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 text-sm"
            autoFocus
          />
          <button
            type="submit"
            disabled={searching}
            className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white font-medium rounded-lg px-4 py-3 text-sm transition-colors flex-shrink-0"
          >
            {searching ? "…" : t.search}
          </button>
        </form>

        {searchError && <p className="text-red-400 text-xs px-1">{searchError}</p>}

        {searchResults && searchResults.length > 0 && (
          <div className="flex flex-col gap-1">
            {searchResults.map((r) => (
              <button
                key={r.steamId}
                onClick={() => router.push(`/players/${r.steamId}`)}
                className="flex items-center gap-3 bg-gray-800 hover:bg-gray-750 rounded-lg px-3 py-2.5 text-left transition-colors"
              >
                {r.avatarUrl ? (
                  <img src={r.avatarUrl} className="w-8 h-8 rounded-full object-cover flex-shrink-0" alt="" />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-gray-700 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white truncate">{r.playerName ?? t.unknown}</p>
                  <p className="text-xs text-gray-500">{r.steamId}</p>
                </div>
                <svg className="w-4 h-4 text-gray-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="w-full max-w-sm flex items-center gap-3">
        <div className="flex-1 h-px bg-gray-800" />
        <span className="text-gray-600 text-xs">{t.orEnterDirectly}</span>
        <div className="flex-1 h-px bg-gray-800" />
      </div>

      {/* Steam ID / URL */}
      <div className="w-full max-w-sm flex flex-col gap-3">
        <p className="text-xs text-gray-500 uppercase tracking-wide">{t.bySteamId}</p>
        <form onSubmit={handleIdSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            value={idInput}
            onChange={(e) => { setIdInput(e.target.value); setIdError(null); }}
            placeholder={t.steamIdPlaceholder}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 text-sm"
          />
          {idError && <p className="text-red-400 text-xs px-1">{idError}</p>}
          <button
            type="submit"
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg py-3 text-sm transition-colors"
          >
            {t.analyzePlayer}
          </button>
        </form>
        <p className="text-gray-600 text-xs">{t.steamIdHint}</p>
      </div>

      <div className="w-full max-w-sm flex items-center gap-3">
        <div className="flex-1 h-px bg-gray-800" />
        <span className="text-gray-600 text-xs">{t.or}</span>
        <div className="flex-1 h-px bg-gray-800" />
      </div>

      {/* Match by ID */}
      <div className="w-full max-w-sm flex flex-col gap-3">
        <p className="text-xs text-gray-500 uppercase tracking-wide">{t.analyzeMatch}</p>
        <form onSubmit={handleMatchSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            inputMode="numeric"
            value={matchId}
            onChange={(e) => { setMatchId(e.target.value); setMatchError(null); }}
            placeholder={t.matchIdPlaceholder}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 text-sm"
          />
          <input
            type="text"
            value={matchSteamId}
            onChange={(e) => { setMatchSteamId(e.target.value); setMatchError(null); }}
            placeholder={t.yourSteamIdPlaceholder}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 text-sm"
          />
          {matchError && <p className="text-red-400 text-xs px-1">{matchError}</p>}
          <button
            type="submit"
            className="w-full bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg py-3 text-sm transition-colors"
          >
            {t.analyzeMatchBtn}
          </button>
        </form>
      </div>

      {/* Demo note */}
      <div className="w-full max-w-sm bg-gray-900/40 border border-gray-800 rounded-lg px-4 py-3 text-xs text-gray-600">
        <p className="font-medium text-gray-500 mb-1">{t.demoTitle}</p>
        <p>
          Steam ID:{" "}
          <button
            className="text-indigo-400 hover:text-indigo-300 font-mono"
            onClick={() => { setIdInput("189158372"); setIdError(null); }}
          >
            189158372
          </button>
        </p>
        <p className="mt-1 text-gray-700">{t.demoHint}</p>
      </div>
    </div>
  );
}
