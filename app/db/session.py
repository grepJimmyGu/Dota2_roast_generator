"""
SQLAlchemy engine + session factory.

DB file path is controlled by the DB_PATH env var (default: dota2_mmr.db in cwd).
check_same_thread=False is required for SQLite when FastAPI handles requests on
multiple threads (default Uvicorn behavior).
"""
from __future__ import annotations
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base

_DB_PATH = os.getenv("DB_PATH", "dota2_mmr.db")
_engine = create_engine(
    f"sqlite:///{_DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def init_db() -> None:
    """Create all tables if they do not already exist. Safe to call on every startup."""
    Base.metadata.create_all(bind=_engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for use inside service functions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency (Depends) for future route-level injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
