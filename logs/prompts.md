# Prompt Log

Chronological record of prompts and requests made during development sessions.

---

## 2026-04-23 — Session 1 (Day 1)

**Prompt:** `read BACKEND_USAGE.md and understand my project context`
Context: Project orientation at start of session.

---

**Prompt:** `I would like you to create a log including my prompt details, meanwhile create a project log files to document overall project goal and daily progress`
Action: Created `PROJECT_LOG.md` and `logs/prompts.md`.

---

**Prompt:** *(Day 1 production-readiness spec — 6 workstreams: persistence, stale/refresh, partial failure, schema, logging, docs)*
Action: Implemented WS-A through WS-F. SQLite + SQLAlchemy DB, cache policy, partial-failure handling, structured logging.

---

**Prompt:** `can we test backend now?`
Action: End-to-end tested all routes against Stratz API (steam_id=189158372). Found and fixed two bugs:
- `_safe_int()` — pandas NaN handling
- `_sum_list()` in match_fetch — scalar kills fix

---

**Prompt:** `save to project log`
Action: Updated PROJECT_LOG.md and logs/prompts.md.

---

## 2026-04-28 — Session 2 (Day 2)

**Prompt:** `let's move on to day 2 with the goal of following prompt, read and optimize before execute`

**Prompt:** *(Full Day 2 spec — interpretation layer, player aggregation, thin frontend, essential UX states)*
Pre-execution analysis performed before any code written. Identified gaps vs existing code.
Action: Built interpretation layer (`derive_phase_labels`, `generate_match_summary`, `generate_player_summary`), schema additions (`strongestPhase`, `weakestPhase`, `shortSummary`), CORS middleware, full Next.js 14 frontend (3 pages, all UX states).

---

**Prompt:** `meanwhile, I think we should enable users to search by steam account name, and allow them to connect and disclose dota profile information easily`
Action: Added `GET /players/search?q=name` Stratz search endpoint. Added My Profile (localStorage), Steam URL / Steam64 parsing, direct match lookup from landing page.

---

**Prompt:** `are we finished with all day 2`
Action: Confirmed complete. Updated BACKEND_USAGE.md with new fields and search endpoint.

---

**Prompt:** *(Day 3 spec — score validation, UX trust-state polish, performance pass, MVP scope finalization, demo readiness)*

**Prompt:** `let's check it out` (checking the running app)

---

## 2026-04-28 — Session 3 (Day 3)

**Prompt:** `I want to segment the game into lane 0-12min mid 13-40, late 40+ min`
Action: Changed `LANE_END=12`, `MID_END=40` in `constants.py`. Propagates automatically through features, benchmarks, scoring. Frontend phase bar labels updated.

---

**Prompt:** *(Day 3 prompt — validation, polish, performance, MVP readiness)*
Action: Executed Day 3 workstreams:
- Fixed `deaths_in_phase` phantom weight (added deaths to query, prorate, benchmark)
- Raised z-score threshold to |z| > 0.4 for strengths/weaknesses
- Added `scored_stat_count` confidence guard to summary generation
- Documented inactive phantom weights in `weights.py`
- Pre-warmed hero name cache on startup
- Dropped `rawStats` from match detail response
- Refresh button: loading state + `lastRefreshedAt` timestamp in stale banner
- Added `gameCloseness` display to match detail
- Added first-load timing notice to loading skeleton
- Added demo Steam ID on landing page

---

## 2026-04-28 — Session 4 (Day 4 — i18n + Roast)

**Prompt:** `I need the website to enable both Chinese and English version`
Action: Built full i18n system — `lib/i18n.ts` (full EN/ZH dictionary), `LanguageContext`, `LanguageToggle`, updated all pages/components. Stat labels mapped to ZH via frontend dict. Language preference persisted in localStorage.

---

**Prompt:** `lane translated to 对线`
Action: Updated `lanePhase` translation from "兵线阶段" to "对线阶段" in i18n dictionary.

---

**Prompt:** `now I want to make it fun, we are going to generate roast based on match details, it should show up as the main part of the user profile as highlight`
Action: Built full AI roast pipeline:
- `src/dota_core/roast/` — `models.py`, `multi_match_summary.py`, `role_pattern_summary.py`, `evidence_selector.py`, `longform_context_builder.py`, `longform_prompt_builder.py`
- `app/services/critique_service.py` — loads 10 matches, calls OpenAI, returns `LongformCritiqueOutput`
- `GET /players/{steam_id}/roast` route
- `RoastCard` frontend component with invite button, spinner, critique display, copy button
- Placed as main highlight section on player overview page

---

**Prompt:** `maybe use chatgpt API`
Action: Swapped Anthropic SDK for OpenAI SDK. Uses `gpt-4o` initially, then `gpt-4.5-preview`, then `gpt-5.5` per user direction.

---

**Prompt:** `ANTHROPIC_API_KEY not configured` / `OpenAI API error: BadRequestError`
Action: Switched to `OPENAI_API_KEY`. Fixed `max_tokens` → `max_completion_tokens` (required by `gpt-5.5`).

---

**Prompt:** `i hope this card can be copied and pasted everywhere`
Action: Added "复制全文" button to `RoastCard` — copies formatted text (title + verdict + critique + punchline + tags) to clipboard via `navigator.clipboard`.

---

**Prompt:** `what are the current tags for different pos for roast`
Action: Audit of active vs inactive tags per position. Identified `deaths_in_phase` missing display label.

---

**Prompt:** *(Full roast tag system spec — 62 tags across 6 categories, `RoastTag` structure, rule functions, registry, helpers, tests)*
Action: Implemented complete roast tag system:
- `roast_tags.py` — 62-tag registry, helper functions
- `tag_rules/common.py` — 10 common rules
- `tag_rules/carry.py` — 9 carry rules
- `tag_rules/mid.py` — 8 mid rules
- `tag_rules/offlane.py` — 7 offlane rules
- `tag_rules/pos4.py` — 6 pos4 rules
- `tag_rules/pos5.py` — 4 pos5 rules
- `tag_engine.py` — `run_tag_rules()` dispatcher
- `tests/test_roast_tags.py` — 31 tests, all passing

---

## 2026-04-29 — Session 5 (Day 4 continued)

**Prompt:** `hello, let's continue our task`
Action: Continued roast tag implementation from where we left off. All tag rule files completed, tests written (31 passing).

---

**Prompt:** `what about "Hero Damage" tag`
Action: Explained dual system: "Hero Damage" is a scoring label from `STAT_LABELS` used in profile summary; `low_hero_damage` is a separate roast tag from the tag engine.

---

**Prompt:** `for roast generation we should only use roast tag, for scoring system label, we should leave that as part of profile summary`
Action: Enforced clean separation:
- Added `roast_tags: list[str]` field to `PlayerMatchStats`
- `critique_service` assigns `stats.roast_tags` from tag engine; never touches `weaknesses`/`strengths`
- `multi_match_summary` and `evidence_selector` now use `roast_tags`
- `longform_context_builder` enriches roast tags with `label_zh` + `roast_angle` for LLM
- All 45 tests passing (31 tag + 14 critique pipeline)

---

**Prompt:** `can I check the historical prompt of the project`
Action: Read `logs/prompts.md` — found it was last updated at Day 2. Updated both `PROJECT_LOG.md` and `logs/prompts.md` with full history through Day 4.

---

## 2026-04-29 — Session 6 (Day 5 — Production Deployment)

**Prompt:** `now I want to push it to production environment, and I will send you a list of prompts, read and provide feedback, let's consolidate into a workable version before moving to execution`

**Prompt:** *(Full production deployment spec — Railway + Vercel, smoke tests, launch blockers, DEPLOYMENT.md)*

**Pre-execution feedback provided:**
- Flagged SQLite ephemeral filesystem risk on Railway — decided to accept ephemeral for demo (Option B)
- Flagged Render 30s timeout as launch blocker for slow Stratz fetches — recommended Railway instead
- Flagged CORS hardcoded to localhost — needs env var before deploy
- Flagged `PYTHONPATH=src` must be in production start command
- Proposed consolidated plan: Railway (backend) + Vercel (frontend)

**Phase B — Production config changes:**
- `app/main.py` — CORS `allow_origins` now reads from `ALLOWED_ORIGINS` env var
- `Procfile` — `PYTHONPATH=src uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- `railway.toml` — healthcheck, restart policy
- `.env.example` — updated with all production env vars
- `DEPLOYMENT.md` — full deploy instructions, env vars, demo walkthrough, known limitations

**Phase C — Railway backend deploy:**
- Connected GitHub repo to Railway, set env vars (`STRATZ_TOKEN`, `OPENAI_API_KEY`, `ALLOWED_ORIGINS`)
- Backend live: `https://dota2-roast-generator.up.railway.app`

**Phase D — Vercel frontend deploy:**

Issues encountered and fixed:
1. Vercel env var KEY field: user confused by UI — clarified to type `NEXT_PUBLIC_API_URL` as key
2. "No Output Directory named public" error — Vercel reading repo root not `frontend/` subdirectory
   - Added `vercel.json` at repo root (failed: `npm install` exited with 1, Node 24 lockfile incompatible with Vercel's Node 18)
   - Fix: moved `vercel.json` inside `frontend/`, added `.node-version` pinning Node 20, instructed user to set Root Directory to `frontend` in Vercel settings
- Frontend live: `https://dota2-roast-generator.vercel.app`

**Phase E — Smoke tests and launch blockers:**

Smoke test results:
- `GET /health` ✅
- `GET /players/{id}/overview` ✅ — SoFate, 20 matches, scores returned
- `GET /matches/{id}` ✅ — Legion Commander, phase breakdown, strengths/weaknesses
- `GET /players/search` ⚠️ — returns empty (Stratz search non-blocking)
- CORS ✅ — after updating `ALLOWED_ORIGINS` in Railway to Vercel URL
- AI roast ✅ — after adding `OPENAI_API_KEY` to Railway and re-seeding DB via overview fetch
  - Generated: title "三号位慈善家", tone "high", 1374 chars, punchline "你开的是团，队友开的是追悼会。"

Launch blockers fixed:
1. CORS rejected Vercel origin → updated `ALLOWED_ORIGINS` in Railway
2. `OPENAI_API_KEY` missing from Railway → added to Variables
3. Empty roast after DB reset → triggered overview fetch first to re-seed SQLite

**Prompt:** `update and refresh the project log and prompt history`
Action: Updated `PROJECT_LOG.md` with live URLs, Day 5 section, new TODOs. Updated `logs/prompts.md` with full Session 6 history.
