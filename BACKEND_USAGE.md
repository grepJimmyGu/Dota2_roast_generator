# Dota 2 MMR Backend — Usage Guide

## Running the server

```bash
PYTHONPATH=src python3 -m uvicorn app.main:app --reload
```

Server starts at `http://localhost:8000`.  
Interactive API docs: `http://localhost:8000/docs`

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `STRATZ_TOKEN` | *(required)* | Stratz API bearer token |
| `DB_PATH` | `dota2_mmr.db` | SQLite database file path |
| `CACHE_FRESHNESS_HOURS` | `6` | How long cached player data stays fresh |

The database file is created automatically on first startup.

---

## Routes

### `GET /health`
Returns `{"status": "ok"}`. Use for uptime checks.

---

### `GET /players/search?q={name}`

Search Stratz for players by display name. Returns up to ~10 results.

**Example:**
```
GET /players/search?q=miracle
```

**Response:** Array of `{ steamId, playerName, avatarUrl }`.

**Notes:**
- Returns empty array (not an error) when no players match.
- Returns 502 on Stratz API failure.
- `q` must be at least 2 characters.

---

### `GET /players/{steam_id}/overview`

Main product entry point. Returns player profile, recent match summaries, aggregate scores, and cache metadata.

**Cache behavior:**

| Condition | Behavior |
|---|---|
| No cached data | Live fetch from Stratz → persist → return |
| Cached, age < `CACHE_FRESHNESS_HOURS` | Return from DB immediately (zero Stratz calls) |
| Cached, age ≥ `CACHE_FRESHNESS_HOURS` | Return from DB with `isStale=true`, `refreshRecommended=true` |

**Example:**
```
GET /players/189158372/overview
```

**Key response fields:**

| Field | Description |
|---|---|
| `steamId` | Steam account ID |
| `playerName` | Display name |
| `avatarUrl` | Avatar image URL |
| `recentMatchCount` | Total matches in response |
| `averageOverallScore` | Average of (positionScore + heroScore)/2 across scored matches |
| `averagePositionScore` | Average position score |
| `averageHeroScore` | Average hero score |
| `strongestPhase` | Phase with highest average position score (`"lane phase"` / `"mid game"` / `"closing"`) |
| `weakestPhase` | Phase with lowest average position score (null if no meaningful gap) |
| `shortSummary` | One-sentence plain-English summary of the player's recent performance |
| `bestHeroes` | Top 3 heroes by avg hero score (min 2 games) |
| `recentTrend` | `"improving"` / `"declining"` / `"stable"` (null if < 4 scored) |
| `isStale` | True when cache age ≥ freshness window |
| `refreshRecommended` | True when `isStale=true` |
| `lastRefreshedAt` | ISO timestamp of last successful refresh |
| `dataCompleteness` | Breakdown of requested / fetched / scored / failed match counts |
| `recentMatches[]` | List of match summaries |

**`dataCompleteness` fields:**

| Field | Description |
|---|---|
| `requestedMatchCount` | Matches returned from the match list |
| `fetchedDetailCount` | Matches for which per-minute detail was available |
| `scoredMatchCount` | Matches that produced complete scores |
| `failedMatchCount` | Matches that could not be scored |

**HTTP errors:**
- `404` — Steam ID not found in Stratz
- `502` — Stratz API failure
- `500` — Internal server error

---

### `POST /players/{steam_id}/refresh`

Force a full refresh for a player, bypassing the freshness window. Fetches and scores the last 100 matches.

> **Warning:** Synchronous — takes 60–120s. Move to an async worker before production use.  
> The service layer is structured so wrapping in `BackgroundTasks` or Celery is straightforward.

**Response:** `{"status": "refreshed", "matchCount": 100}`

**HTTP errors:**
- `404` — Steam ID not found
- `502` — Stratz API failure

---

### `GET /matches/{match_id}?steam_id={steam_id}`

Full scoring analysis for a single match. Checks the DB cache before calling Stratz.

If scoring fails (e.g. benchmark data unavailable), returns available identity fields with `isPartial=true` rather than a 500.

**Example:**
```
GET /matches/8212345678?steam_id=189158372
```

**Key response fields:**

| Field | Description |
|---|---|
| `matchId` | Match ID |
| `heroId` / `heroName` | Hero played |
| `position` | 1–5 |
| `result` | `"win"` / `"loss"` / null |
| `durationMinutes` | Match length |
| `overallPositionScore` | 0–100 vs all heroes at same position + bracket |
| `overallHeroScore` | 0–100 vs same hero at same position + bracket |
| `phaseBreakdown` | `{early_game, mid_game, late_game}` each with `positionScore` + `heroScore` |
| `gameCloseness` | 0.0–1.0 kill ratio (1.0 = perfectly even) |
| `strongestPhase` | Phase with highest position score for this match |
| `weakestPhase` | Phase with lowest position score for this match |
| `shortSummary` | One-sentence plain-English match summary |
| `topStrengths` | Top 3 stat labels where player exceeded benchmark |
| `topWeaknesses` | Bottom 3 stat labels where player fell short |
| `hasBenchmarkContext` | True when bracket + position context was resolved |
| `isPartial` | True when scoring completed partially (some scores may be null) |
| `benchmarkContext` | `{bracket, position, heroId}` used for scoring |
| `rawStats` | Per-minute arrays: networthPerMinute, heroDamagePerMinute, lastHitsPerMinute, goldPerMinute |

**HTTP errors:**
- `404` — Match not found or player not in match
- `502` — Stratz API failure
- `500` — Internal server error

---

## Scoring overview

Two parallel score tracks per match, each [0–100]:

| Track | Benchmark |
|---|---|
| **Position score** | All heroes at this position + bracket |
| **Hero score** | Same hero at this position + bracket |

Three phases:

| Phase | Minutes | Weight |
|---|---|---|
| `early_game` | 0–12 | 30% |
| `mid_game` | 13–40 | 35% |
| `late_game` | 40+ | 35% |

Overall score = weighted average of available phases.

---

## Stale / refresh behavior

```
First request for a Steam ID
  └─ no cache → live fetch → persist to DB → return

Subsequent requests within CACHE_FRESHNESS_HOURS (default 6h)
  └─ cache hit → return from DB immediately (isStale=false)

Subsequent requests after freshness window
  └─ return from DB (isStale=true, refreshRecommended=true)
  └─ call POST /refresh to force a re-fetch

POST /players/{id}/refresh
  └─ always fetches live regardless of cache age
```

---

## Partial result behavior

The backend never fails an entire player response because one match failed.

- Each match's detail fetch and scoring are attempted independently
- Failures are counted and returned in `dataCompleteness`
- Failed matches appear in `recentMatches[]` with `scoringPending=true` and null score fields
- `failedMatchCount > 0` does not affect the scores of successful matches

For `GET /matches/{match_id}`:
- If scoring fails, `isPartial=true` is set and identity fields are still returned
- A total 404/502 is only raised if the detail payload itself cannot be retrieved

---

## Observability

All requests emit structured log lines to stdout via the `dota.backend` logger:

```
# Cache hit
2026-04-23 12:00:00 INFO     dota.backend [overview] steam_id=189158372 start
2026-04-23 12:00:00 INFO     dota.backend [overview] steam_id=189158372 cache_hit=True is_stale=False duration_ms=3

# Live refresh
2026-04-23 12:00:00 INFO     dota.backend [overview] steam_id=189158372 start
2026-04-23 12:00:00 INFO     dota.backend [overview] steam_id=189158372 cache_hit=False
2026-04-23 12:00:00 INFO     dota.backend [refresh]  steam_id=189158372 start matches_requested=20
2026-04-23 12:00:18 INFO     dota.backend [refresh]  steam_id=189158372 matches_fetched=20
2026-04-23 12:00:36 INFO     dota.backend [refresh]  steam_id=189158372 details_fetched=9 scored=9 failed=1
2026-04-23 12:00:36 WARNING  dota.backend [refresh]  steam_id=189158372 match_id=8212345678 scoring_failed detail_ok=True error=ValueError
2026-04-23 12:00:36 INFO     dota.backend [refresh]  steam_id=189158372 complete duration_ms=18432
2026-04-23 12:00:36 INFO     dota.backend [overview] steam_id=189158372 complete duration_ms=18435

# Match detail
2026-04-23 12:00:00 INFO     dota.backend [match] match_id=8212345678 steam_id=189158372 start
2026-04-23 12:00:00 INFO     dota.backend [match] match_id=8212345678 steam_id=189158372 detail_source=cache
2026-04-23 12:00:00 INFO     dota.backend [match] match_id=8212345678 steam_id=189158372 is_partial=False duration_ms=44
```

---

## Known TODOs

- [ ] Move `POST /refresh` to async background worker (Celery / FastAPI BackgroundTasks)
- [ ] Replace `lru_cache` benchmark cache with Redis for multi-worker deployments
- [ ] Add `rank` field derivation from `averageRank` distribution
- [ ] Replace `hero_name()` live API call with a static JSON asset (eliminates cold-start Stratz call)
- [ ] Add `fetchedDetailCount` accuracy for cached path (currently proxied by `scoredMatchCount`)
- [ ] Persist `strongestPhase` / `weakestPhase` / `shortSummary` to DB (currently computed on-the-fly)
- [ ] Implement hero characteristic scoring layer (layer 2 of the scoring design)
