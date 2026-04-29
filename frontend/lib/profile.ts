const KEY = "dota_my_profile";

export interface SavedProfile {
  steamId: number;
  playerName: string | null;
  avatarUrl: string | null;
}

export function loadProfile(): SavedProfile | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as SavedProfile) : null;
  } catch {
    return null;
  }
}

export function saveProfile(profile: SavedProfile): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(profile));
  } catch {}
}

export function clearProfile(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {}
}
