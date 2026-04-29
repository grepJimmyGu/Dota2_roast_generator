# Dota 2 Roast Generator

A full-stack Dota 2 performance analysis platform that scores your matches, explains what you did well and poorly, and generates an AI-powered long-form critique of your recent gameplay — in Chinese.

---

## What it does

1. **Enter a Steam ID** — the app fetches your recent ranked matches via the [Stratz](https://stratz.com) GraphQL API
2. **Player overview** — see your average role score, hero score, strongest/weakest phase, recent trend, and best heroes
3. **Match detail** — per-match phase breakdown (lane / mid / late), top strengths and weaknesses, plain-language summary
4. **AI Roast** — click 🔥 开烤 to generate a 350+ word sarcastic Chinese critique of your last 10 matches, grounded in your actual stats

Supports **English and Chinese (中文)** — toggle in the top-right corner.

---

## Screenshots

| Landing | Player Overview | Match Detail | AI Roast |
|---|---|---|---|
| Steam ID / name search, My Profile | Scores, phase labels, recent matches | Phase bar, strengths/weaknesses | Long-form sarcastic critique |

---

## Tech Stack

**Backend**
- Python + FastAPI
- SQLite + SQLAlchemy (caching layer)
- [Stratz GraphQL API](https://api.stratz.com/graphql) for match data and benchmarks
- OpenAI API (`gpt-5.5`) for critique generation

**Frontend**
- Next.js 14 (App Router)
- Tailwind CSS
- EN / 中文 i18n via React context

---

## How Scoring Works

Each match is scored across two parallel tracks, broken into three phases:

| Phase | Minutes | Weight |
|---|---|---|
| Lane | 0–12 | 30% |
| Mid | 13–40 | 35% |
| Late | 40+ | 35% |

**Position score** — how you performed vs all heroes at your role and rank bracket  
**Hero score** — how you performed vs players on the same hero at your role and rank bracket

Scores are z-score based, scaled to [0–100]. 50 = exactly average for your bracket.

Role-specific factors scored per phase:

| Factor | Roles |
|---|---|
| Net worth, last hits, denies | Carry |
| Lane presence (vacancy time penalty) | Carry |
| Rune control | Mid |
| Aggression (frequency × damage per instance) | Offlane |
| Vision control (obs + sentry + dewards) | Support (4, 5) |
| Tower damage, kills, assists, deaths | All |

---

## AI Roast System

The roast pipeline is data-grounded, not random insults.

### Tag engine
62 structured gameplay tags across 6 categories (common + per role). Each tag has a Chinese label, severity score, and a Dota-flavored roast angle. Tags only fire when the required data is available.

Examples:
- `farm_black_hole` — 刷钱黑洞 — "把全队资源吸进去，再把作用蒸发掉"
- `comeback_thrower` — 优势局战犯 — "对面本来都准备点了，是你把他们重新劝回游戏"
- `no_initiation` — 没先手 — "团战没人开，你站在那里像等公交"

### Critique pipeline
```
last 10 matches
  → tag engine (per match)
  → multi-match summary + role pattern analysis + evidence selection
  → LLM context + prompt
  → OpenAI → 350+ word Chinese critique
  → copy to clipboard
```

The critique cites concrete match examples, analyzes by role, and ends with a punchline.

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- A [Stratz API token](https://stratz.com/api)
- An OpenAI API key (for the roast feature)

### Backend

```bash
cd dota2_MMR

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your STRATZ_TOKEN and OPENAI_API_KEY

# Start the API server
PYTHONPATH=src python3 -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd dota2_MMR/frontend

npm install
npm run dev
# Opens at http://localhost:3000
```

---

## API Reference

| Route | Description |
|---|---|
| `GET /health` | Health check |
| `GET /players/{steam_id}/overview` | Player overview with scores and recent matches |
| `GET /players/{steam_id}/roast` | Generate AI critique of last 10 matches |
| `POST /players/{steam_id}/refresh` | Force re-fetch from Stratz (bypasses cache) |
| `GET /players/search?q={name}` | Search players by Steam display name |
| `GET /matches/{match_id}?steam_id={id}` | Full match analysis with phase breakdown |

Cache behavior: player data is cached for 6 hours. First load for a new player takes 30–60s while fetching from Stratz.

---

## Project Structure

```
dota2_MMR/
├── app/                        # FastAPI application
│   ├── routes/                 # API route handlers
│   ├── services/               # Business logic
│   ├── repositories/           # DB access layer
│   └── db/                     # SQLAlchemy models + session
├── src/dota_core/              # Core domain modules
│   ├── ingest/                 # Stratz API fetching
│   ├── scoring/                # Phase scoring engine
│   ├── benchmarks/             # Bracket-aware benchmarks
│   ├── domain/                 # Hero metadata
│   └── roast/                  # AI critique pipeline
│       ├── tag_rules/          # Per-role tag rule functions
│       ├── roast_tags.py       # 62-tag registry
│       ├── tag_engine.py       # Tag dispatcher
│       ├── multi_match_summary.py
│       ├── role_pattern_summary.py
│       ├── evidence_selector.py
│       ├── longform_context_builder.py
│       └── longform_prompt_builder.py
├── frontend/                   # Next.js 14 frontend
│   ├── app/                    # Pages (landing, overview, match)
│   ├── components/             # UI components
│   ├── contexts/               # Language context
│   └── lib/                    # Types, i18n, utilities
└── tests/                      # Unit tests (45 total)
```

---

## Known Limitations

- **Refresh is synchronous** — `POST /refresh` fetches 100 matches and takes 60–120s. A background worker is the right fix but not yet implemented.
- **Some scoring factors inactive** — `health_status`, `vision_control`, `rune_control` are defined in the scoring weights but Stratz doesn't expose the required per-minute data in its current API.
- **AI roast always in Chinese** — the critique prompt is Chinese-only for now. English critique is a future addition.
- **Single-player DB** — if two players appear in the same match and both are analyzed, the second fetch overwrites the first in `match_details`. Acceptable at MVP scale.

---

## License

MIT
