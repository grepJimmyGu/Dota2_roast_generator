import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import init_db
from app.routes import health, players, matches
from dota_core.domain.heroes import hero_name as _prewarm_heroes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log = logging.getLogger("dota.backend")
    log.info("DB initialized")
    try:
        _prewarm_heroes(1)   # one call fetches and caches all hero names for the session
        log.info("Hero name cache primed")
    except Exception:
        log.warning("Hero name cache prewarm failed — names will resolve on first request")
    yield


app = FastAPI(
    title="Dota 2 MMR Analyzer",
    version="0.2.0",
    description="Per-match, per-phase performance scoring backed by Stratz data.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(players.router, prefix="/players")
app.include_router(matches.router, prefix="/matches")
