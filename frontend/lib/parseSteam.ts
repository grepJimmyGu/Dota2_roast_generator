// Steam64 IDs are 17-digit numbers starting with 765611979...
// Steam32 = Steam64 - 76561197960265728
const STEAM64_BASE = BigInt("76561197960265728");
const STEAM64_MIN  = BigInt("76561197960265728");

export interface ParseResult {
  steamId: string | null;
  error: string | null;
}

export function parseSteamInput(raw: string): ParseResult {
  const input = raw.trim();
  if (!input) return { steamId: null, error: "Enter a Steam ID or profile URL." };

  // steamcommunity.com/profiles/76561198...
  const profileMatch = input.match(/steamcommunity\.com\/profiles\/(\d{17})/);
  if (profileMatch) {
    return { steamId: steam64to32(profileMatch[1]), error: null };
  }

  // steamcommunity.com/id/vanity — not resolvable client-side
  if (/steamcommunity\.com\/id\//i.test(input)) {
    return {
      steamId: null,
      error: 'Vanity URLs aren\'t supported. Use your numeric profile URL (steamcommunity.com/profiles/...) or find your Steam ID below.',
    };
  }

  // Pure digits
  if (/^\d+$/.test(input)) {
    const n = BigInt(input);
    if (n > STEAM64_MIN) {
      // Steam64 ID
      return { steamId: steam64to32(input), error: null };
    }
    // Assume Steam32
    return { steamId: input, error: null };
  }

  return {
    steamId: null,
    error: "Couldn't parse that. Enter a numeric Steam ID or steamcommunity.com/profiles/... URL.",
  };
}

function steam64to32(steam64: string): string {
  return (BigInt(steam64) - STEAM64_BASE).toString();
}
