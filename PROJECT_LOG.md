# Dota 2 MMR — Project Log

## Project Goal

Build a per-match performance scoring system for Dota 2 ranked games. Given any player's Steam ID, the system fetches their recent matches via the Stratz GraphQL API and scores each match across two parallel tracks:

- **Position score** — how well the player performed relative to all heroes at the same role and rank bracket
- **Hero score** — how well the player performed relative to other players on the same hero, at the same role and rank bracket

Each match is broken into three phases (lane 0–12 min, mid 13–40 min, late 40+ min) with weighted contributions. The end product is a REST API (FastAPI) + Next.js frontend that surfaces per-match scores, player averages, trend analysis, strength/weakness breakdowns, and an AI-generated long-form critique.

---

## Live Deployment

| Service | URL |
|---|---|
| Frontend | https://dota2-roast-generator.vercel.app |
| Backend | https://dota2-roast-generator.up.railway.app |

Platform: **Vercel** (Next.js frontend) + **Railway** (FastAPI backend)

---

## Architecture

| Layer | Location | Purpose |
|---|---|---|
| API routes | `app/routes/` | FastAPI endpoints (players, matches, health) |
| Services | `app/services/` | Orchestrate ingest, scoring, critique generation |
| Stratz client | `src/dota_core/client.py` | GraphQL HTTP client (Bearer auth) |
| Ingest | `src/dota_core/ingest/` | Fetch match list, match detail, benchmarks, player search |
| Scoring | `src/dota_core/scoring/` | Phase + role scoring logic |
| Benchmarks | `src/dota_core/benchmarks/` | Bracket-aware benchmark fetch + heuristic priors |
| Domain models | `src/dota_core/domain/` | Shared data models and hero metadata |
| Roast pipeline | `src/dota_core/roast/` | Tag engine, multi-match analysis, LLM critique generation |
| Frontend | `frontend/` | Next.js 14 + Tailwind, EN/ZH bilingual |

---

## Scoring Design

### Two-layer plan
1. **Role-based base scoring** — scores against position peers regardless of hero — **DONE**
2. **Hero characteristic scoring** — adjusts for hero-specific mechanics on top — **TODO**

### Phase boundaries
| Phase | Minutes | Overall Weight |
|---|---|---|
| Lane | 0–12 | 30% |
| Mid | 13–40 | 35% |
| Late | 40+ | 35% |

### Role-based factors

| Factor | Positions | Phase |
|---|---|---|
| net_worth_gain, last_hits, denies | Pos 1 | all |
| vacancy_time (idle farming penalty) | Pos 1 only | all (weight escalates −10/−15/−20%) |
| rune_control | Pos 2 only | lane only |
| aggression (freq × per-instance dmg) | Pos 3 only | all (weight escalates 12/18/22%) |
| health_status (avg HP% in lane) | all except Huskar (hero 59) | lane only |
| vision_control (obs+sentry+dewards) | Pos 4, 5 | all, capped 15% |
| tower_damage | all | lane ≤10%, mid 15–25%, late 20–25% (support capped 15%) |
| deaths_in_phase (prorated from total) | all | all |

### Inactive stat weights (data not yet available from Stratz)
- `xp_gain` — no XP per-minute array in MATCH_DETAILED
- `health_status` — requires healthPerMinute arrays
- `rune_control` — requires runePickups events
- `vision_control` — requires ward events

---

## Roast / Critique System

### Two separate signal layers (intentional separation)
| Signal | Source | Used by |
|---|---|---|
| `weaknesses` / `strengths` | Scoring z-scores → `STAT_LABELS` | Player profile summary, match detail page |
| `roast_tags` | Tag engine → `ROAST_TAG_REGISTRY` | LLM critique generation only |

### Tag registry
- 62 total tags across 6 categories
- 12 common (all roles) + 10 per role × 5 roles
- Each tag has: `tag_id`, `label_zh`, `label_en`, `description`, `severity_score`, `roles`, `roast_angle`, `evidence_fields`
- Tags requiring unavailable data (items, wards, stuns) are registered but never fire

### Critique pipeline
```
GET /players/{steam_id}/roast
  → load last 10 scored matches from DB
  → run tag engine per match → roast_tags
  → multi_match_summary + role_pattern_summary + evidence_selector
  → build_longform_critique_context
  → build_longform_critique_prompt (system + user)
  → OpenAI gpt-5.5 → JSON response
  → LongformCritiqueOutput
```

---

## Open TODOs

- [x] Persist scored match data to DB — done Day 1
- [x] Populate `strongestPhase` / `weakestPhase` — done Day 2
- [x] `deaths_in_phase` scoring — done Day 3
- [x] Roast tag system — done Day 4
- [x] Production deployment — done Day 5 (Vercel + Railway)
- [ ] Add Railway persistent volume for SQLite (currently ephemeral — DB resets on redeploy)
- [ ] Move `POST /refresh` to async background worker
- [ ] Replace `lru_cache` benchmark cache with Redis for multi-worker deployments
- [ ] Replace `hero_name()` live API call with a static asset bundle
- [ ] Implement hero characteristic scoring layer (layer 2)
- [ ] Persist `strongestPhase` / `weakestPhase` / `shortSummary` to DB
- [ ] Add hero images from Dota CDN
- [ ] Frontend: mini sparkline for score trend on player overview
- [ ] Activate ward/stun/item data from Stratz to unlock gated roast tags
- [ ] Add Chinese summary generation (currently English only from scoring engine)
- [ ] Future RAG: roast example database, hero-specific punchlines, role writing patterns

---

## Day 1 — Production Readiness (2026-04-23)

| WS | Scope | Key files |
|---|---|---|
| WS-A | SQLite + SQLAlchemy persistence | `app/db/`, `app/repositories/` |
| WS-B | Stale/refresh policy — 6hr freshness, Case A/B/C | `player_service.py`, `config.py` |
| WS-C | Partial-failure handling | services |
| WS-D | Schema stabilization — `isStale`, `dataCompleteness`, `isPartial` | `schemas.py` |
| WS-E | Structured logging via `dota.backend` logger | `main.py`, services |
| WS-F | BACKEND_USAGE.md | docs |

Design decisions: SQLite + SQLAlchemy sync, `raw_payload` JSON blob for re-scoring, `match_id` sole PK.

---

## Day 2 — Interpretation + Frontend (2026-04-28)

| WS | Scope | Key files |
|---|---|---|
| WS-A | Interpretation layer — phase labels, match summary, player summary | `scoring_utils.py` |
| WS-B | Schema additions — `strongestPhase`, `weakestPhase`, `shortSummary` | `schemas.py` |
| WS-C | Service wiring | `match_service.py`, `player_service.py` |
| WS-D | CORS middleware | `main.py` |
| WS-E | Next.js 14 + Tailwind frontend — 3 pages, all UX states | `frontend/` |
| WS-F | Docs update | `PROJECT_LOG.md`, `BACKEND_USAGE.md` |

Beyond spec (user requests):
- Name search (`GET /players/search`)
- My Profile (localStorage persistence + Steam URL/Steam64 parsing)
- Direct match lookup from landing page
- Phase boundary change: 0–12 / 13–40 / 40+

---

## Day 3 — Validation + Polish + Performance (2026-04-28)

| Fix | Detail |
|---|---|
| `deaths_in_phase` | Added `deaths` to `MATCH_DETAILED` query, prorated from total, added to benchmark transform |
| Strengths/weaknesses threshold | Raised from z > 0 to \|z\| > 0.4 — removes near-average noise |
| Summary confidence guard | `scored_stat_count < 3` → "Limited benchmark data" message |
| Phantom weights documented | `xp_gain`, `health_status`, `rune_control` clearly marked as inactive in `weights.py` |
| Hero name pre-warm | `_fetch_hero_names()` called on startup lifespan |
| `rawStats` removed | Dropped from `MatchDetailResponse` — was serialized but never rendered |
| Refresh UX | Loading state + `lastRefreshedAt` timestamp in stale banner |
| Benchmark unavailable state | Match detail shows explanation when `hasBenchmarkContext=false` |
| `gameCloseness` surfaced | Shown as "Even game / Moderately one-sided / Heavily one-sided" |
| First-load timing | Loading skeleton shows "30–60s for new players" notice |
| Demo Steam ID | Clickable example on landing page |

---

## Day 5 — Production Deployment (2026-04-29)

| Step | Outcome |
|---|---|
| Backend on Railway | ✅ `https://dota2-roast-generator.up.railway.app` |
| Frontend on Vercel | ✅ `https://dota2-roast-generator.vercel.app` |
| CORS configured | ✅ `ALLOWED_ORIGINS` env var, Railway → Vercel origin |
| Health check | ✅ `/health` returns `{"status":"ok"}` |
| Player overview | ✅ Scores, phases, summary, 20 matches |
| Match detail | ✅ Phase breakdown, strengths/weaknesses |
| AI roast | ✅ OpenAI `gpt-5.5` generating in production |
| End-to-end flow | ✅ Steam ID → overview → match → roast fully working |

Deployment config added:
- `Procfile` — `PYTHONPATH=src uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- `railway.toml` — health check path, restart policy
- `frontend/vercel.json` — framework declaration
- `frontend/.node-version` — pins Node 20 for Vercel compatibility
- `DEPLOYMENT.md` — full deploy instructions, env vars, demo walkthrough

Launch blockers encountered and fixed:
- CORS: `allow_origins` hardcoded to localhost → moved to `ALLOWED_ORIGINS` env var
- Vercel build: Root Directory not set → added `frontend/vercel.json`, pinned Node 20
- OpenAI `AuthenticationError`: `OPENAI_API_KEY` missing from Railway → added to Variables
- Empty roast after Railway redeploy: ephemeral SQLite reset → hit overview first to re-seed DB

Known production limitations:
- SQLite is ephemeral — DB resets on Railway redeploy (data re-fetches from Stratz automatically)
- Player name search returns empty in production (Stratz search schema behaviour)
- `POST /refresh` (100 matches) may be slow for long Stratz fetches

---

## Day 4 — i18n + AI Roast System (2026-04-28 / 2026-04-29)

### i18n (EN / 中文)
- `lib/i18n.ts` — full translation dictionary (EN + ZH) for all UI strings
- `contexts/LanguageContext.tsx` — React context with localStorage persistence
- `components/LanguageToggle.tsx` — toggle button in layout header
- All pages and components updated to use `useLanguage()` hook
- Stat labels (`topStrengths`/`topWeaknesses`) mapped to ZH via `STAT_LABEL` frontend dict
- Phase labels translated; backend-generated `shortSummary` remains English (TODO)

### AI Roast / Critique Pipeline
New module: `src/dota_core/roast/`

| File | Purpose |
|---|---|
| `models.py` | `PlayerMatchStats`, `LongformCritiqueOutput` dataclasses |
| `multi_match_summary.py` | `summarize_last_matches()` — 25 aggregate fields |
| `role_pattern_summary.py` | `summarize_role_patterns()` — per-role stats + critique angle |
| `evidence_selector.py` | `select_critique_evidence()` — worst loss, best win, typical, funniest |
| `longform_context_builder.py` | Assembles full LLM context; enriches roast tags with label + angle |
| `longform_prompt_builder.py` | System + user prompt; 350-word minimum, safety constraints |
| `roast_tags.py` | 62-tag registry + helper functions |
| `tag_rules/common.py` | 10 common rules (all roles) |
| `tag_rules/carry.py` | 9 carry rules |
| `tag_rules/mid.py` | 8 mid rules |
| `tag_rules/offlane.py` | 7 offlane rules |
| `tag_rules/pos4.py` | 6 pos4 rules |
| `tag_rules/pos5.py` | 4 pos5 rules |
| `tag_engine.py` | `run_tag_rules()` dispatcher + `player_stats_to_dict()` |

Service + API:
- `app/services/critique_service.py` — loads 10 matches from DB, runs tags, calls OpenAI `gpt-5.5`
- `GET /players/{steam_id}/roast?lang=zh` — new route

Frontend:
- `components/RoastCard.tsx` — invite button → spinner → critique card with copy button
- Placed as main highlight on player overview page above Best Heroes

Signal separation (enforced):
- `weaknesses`/`strengths` from scoring system → profile summary only
- `roast_tags` from tag engine → LLM critique only; never merged

Tests: 45 total (31 tag system + 14 critique pipeline), all passing.

---

## Daily Progress

### 2026-04-09
- Project started. Established Stratz GraphQL client and initial match fetch pipeline.

### 2026-04-23
- Day 1 complete. Backend cache-backed, partial-failure resilient, observable.
- Two bugs fixed: `_safe_int()` for pandas NaN, `_sum_list()` for scalar kill counts.
- All routes tested against live Stratz API (steam_id=189158372).

### 2026-04-28
- Day 2 complete. Interpretation layer, frontend, all UX states.
- Day 3 complete. Deaths scoring fix, threshold tuning, performance polish.
- Day 4 started: i18n (EN/ZH), roast tag system (62 tags), AI critique pipeline.
- Phase boundaries changed to 0–12 / 13–40 / 40+ per product direction.
- OpenAI (`gpt-5.5`) integrated for critique generation.

### 2026-04-29
- Day 4 continued. Roast tag system finalized.
- Signal separation enforced: scoring labels ↔ roast tags are now independent.
- `roast_tags` field added to `PlayerMatchStats`; critique pipeline uses only roast tags.
- All 45 tests passing.
- GitHub repo created: https://github.com/grepJimmyGu/Dota2_roast_generator
- README.md added with full project overview, setup guide, and architecture docs.
- Day 5: Production deployment sprint.
  - Backend deployed to Railway (`dota2-roast-generator.up.railway.app`)
  - Frontend deployed to Vercel (`dota2-roast-generator.vercel.app`)
  - CORS configured via `ALLOWED_ORIGINS` env var
  - `Procfile` + `railway.toml` added for Railway deployment
  - `DEPLOYMENT.md` written with full deploy instructions and demo walkthrough
  - All production smoke tests passed: health, overview, match detail, AI roast
  - AI roast verified working end-to-end in production (title: 三号位慈善家, tone: high)
