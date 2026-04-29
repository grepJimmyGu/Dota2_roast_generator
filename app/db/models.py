"""
SQLAlchemy ORM models — one table per domain concept.

Design notes:
- match_id is the sole PK on match/detail/score tables (MVP single-player focus).
  Known limit: if two different Steam IDs are in the same match and both are looked up,
  the second upsert overwrites the first in match_details. Acceptable at this scale.
- raw_payload (JSON blob) on match_details lets us re-run scoring from cache without
  re-calling Stratz.
- No FK constraints declared (SQLite doesn't enforce them by default; keep schema simple).
"""
from __future__ import annotations
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Player(Base):
    __tablename__ = "players"

    steam_id          = Column(Integer, primary_key=True)
    player_name       = Column(String,  nullable=True)
    avatar_url        = Column(String,  nullable=True)
    rank              = Column(Integer, nullable=True)

    # Refresh tracking
    last_refreshed_at  = Column(DateTime, nullable=True)   # last successful refresh
    last_attempted_at  = Column(DateTime, nullable=True)   # last attempt (any outcome)
    refresh_status     = Column(String,   nullable=True)   # "ok" | "error" | "pending"
    error_message      = Column(Text,     nullable=True)


class Match(Base):
    __tablename__ = "matches"

    match_id         = Column(Integer, primary_key=True)
    steam_id         = Column(Integer, nullable=False, index=True)
    hero_id          = Column(Integer, nullable=True)
    hero_name        = Column(String,  nullable=True)
    position         = Column(Integer, nullable=True)
    start_time       = Column(Integer, nullable=True)   # unix epoch
    duration_seconds = Column(Integer, nullable=True)
    won              = Column(Boolean, nullable=True)
    kills            = Column(Integer, nullable=True)
    deaths           = Column(Integer, nullable=True)
    assists          = Column(Integer, nullable=True)
    average_rank     = Column(Integer, nullable=True)
    radiant_kills    = Column(Integer, nullable=True)
    dire_kills       = Column(Integer, nullable=True)


class MatchDetail(Base):
    __tablename__ = "match_details"

    match_id    = Column(Integer, primary_key=True)
    raw_payload = Column(JSON,     nullable=False)   # full dict from get_match_detail()
    fetched_at  = Column(DateTime, nullable=False, default=datetime.utcnow)


class MatchScore(Base):
    __tablename__ = "match_scores"

    match_id                   = Column(Integer, primary_key=True)
    steam_id                   = Column(Integer, nullable=False, index=True)

    overall_position_score     = Column(Float, nullable=True)
    overall_hero_score         = Column(Float, nullable=True)

    early_game_position_score  = Column(Float, nullable=True)
    early_game_hero_score      = Column(Float, nullable=True)
    mid_game_position_score    = Column(Float, nullable=True)
    mid_game_hero_score        = Column(Float, nullable=True)
    late_game_position_score   = Column(Float, nullable=True)
    late_game_hero_score       = Column(Float, nullable=True)

    game_closeness             = Column(Float, nullable=True)
    top_strengths              = Column(JSON,  nullable=True)   # list[str]
    top_weaknesses             = Column(JSON,  nullable=True)   # list[str]

    scored_at                  = Column(DateTime, nullable=False, default=datetime.utcnow)
