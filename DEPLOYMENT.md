# Deployment Guide

## Live URLs

| Service | URL |
|---|---|
| Frontend | *(set after Vercel deploy)* |
| Backend | *(set after Railway deploy)* |

---

## Stack

- **Frontend**: Next.js 14 → [Vercel](https://vercel.com)
- **Backend**: FastAPI + Python → [Railway](https://railway.app)
- **Database**: SQLite (ephemeral on Railway — data re-fetches from Stratz on first visit after redeploy)

---

## Required Environment Variables

### Backend (Railway)

| Variable | Description |
|---|---|
| `STRATZ_TOKEN` | Stratz GraphQL API bearer token — get from https://stratz.com/api |
| `OPENAI_API_KEY` | OpenAI API key — required for AI roast feature |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins — set to your Vercel URL e.g. `https://your-app.vercel.app` |
| `DB_PATH` | Optional — defaults to `dota2_mmr.db` in working dir. Set to `/data/dota2_mmr.db` if using a Railway persistent volume. |

### Frontend (Vercel)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Full URL of your Railway backend — e.g. `https://your-backend.up.railway.app` |

---

## Deploy Backend (Railway)

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Select the `Dota2_roast_generator` repo
3. Railway auto-detects Python via `railway.toml`
4. In **Variables**, add `STRATZ_TOKEN`, `OPENAI_API_KEY`, `ALLOWED_ORIGINS`
5. Wait for deploy — check logs for `Application startup complete`
6. Verify: `GET https://your-backend.up.railway.app/health` → `{"status":"ok"}`

Start command (already in `railway.toml`):
```
PYTHONPATH=src uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## Deploy Frontend (Vercel)

1. Go to [vercel.com](https://vercel.com) → New Project → Import from GitHub
2. Set **Root Directory** to `frontend`
3. Framework preset: **Next.js** (auto-detected)
4. In **Environment Variables**, add:
   - `NEXT_PUBLIC_API_URL` = `https://your-backend.up.railway.app`
5. Deploy — Vercel assigns a `*.vercel.app` URL
6. Copy that URL and update `ALLOWED_ORIGINS` in Railway to include it
7. Redeploy Railway backend (or it picks it up on next restart)

---

## Update CORS After Frontend Deploy

Once you have the Vercel URL, update Railway's `ALLOWED_ORIGINS`:

```
ALLOWED_ORIGINS=https://your-app.vercel.app
```

Railway redeploys automatically when env vars change.

---

## Local Development

```bash
# Backend
cd dota2_MMR
cp .env.example .env   # fill in STRATZ_TOKEN and OPENAI_API_KEY
PYTHONPATH=src python3 -m uvicorn app.main:app --reload --port 8000

# Frontend
cd dota2_MMR/frontend
npm install
npm run dev            # http://localhost:3000
```

Frontend reads `NEXT_PUBLIC_API_URL` from `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Demo Walkthrough

1. Open the frontend URL
2. Enter Steam ID `189158372` (click the demo button) → **Analyze Player**
3. Wait 30–60s on first load (fetching from Stratz)
4. View player overview — scores, phase labels, recent matches
5. Click any match → match detail with phase breakdown and strengths/weaknesses
6. On overview page, click **🔥 开烤** → AI generates a 350+ word Chinese critique
7. Click **复制全文** to copy the critique for sharing

---

## Known Limitations

| Limitation | Impact |
|---|---|
| SQLite is ephemeral on Railway | Data re-fetches from Stratz after each redeploy (~30–60s first visit) |
| `POST /refresh` (100 matches) takes 60–120s | May timeout on slow connections; core overview flow unaffected |
| AI roast always generates in Chinese | English critique not yet implemented |
| No auth | Any Steam ID is publicly queryable |
| Hero name cache is in-process | Resets on each Railway restart (re-fetches once on startup) |

---

## What Is Intentionally Deferred

- Async background workers for refresh
- Persistent SQLite volume / Postgres migration
- Auth / rate limiting
- English AI critique
- Hero images from Dota CDN
- Advanced hero-characteristic scoring (layer 2)
