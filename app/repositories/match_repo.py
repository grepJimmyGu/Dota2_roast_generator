"""
MatchRepository — store and load match rows and raw detail payloads.
"""
from __future__ import annotations
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import Match, MatchDetail


class MatchRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Match rows (summary data from the player match list)
    # ------------------------------------------------------------------

    def get_for_player(self, steam_id: int, limit: int = 20) -> list[Match]:
        """Return up to `limit` matches for a player, most recent first."""
        return (
            self.db.query(Match)
            .filter(Match.steam_id == steam_id)
            .order_by(Match.start_time.desc())
            .limit(limit)
            .all()
        )

    def upsert_many(self, rows: list[dict]) -> None:
        """Bulk insert-or-update match rows. Commits once at the end."""
        for row in rows:
            match = self.db.get(Match, row["match_id"])
            if match is None:
                match = Match(**row)
                self.db.add(match)
            else:
                for key, val in row.items():
                    setattr(match, key, val)
        self.db.commit()

    # ------------------------------------------------------------------
    # Match detail payloads (per-minute stat arrays, player-specific)
    # ------------------------------------------------------------------

    def get_detail(self, match_id: int) -> dict | None:
        """Return the cached raw payload dict, or None if not yet fetched."""
        row = self.db.get(MatchDetail, match_id)
        return row.raw_payload if row else None

    def upsert_detail(self, match_id: int, payload: dict) -> None:
        """Store (or overwrite) the raw detail payload for a match."""
        row = self.db.get(MatchDetail, match_id)
        if row is None:
            row = MatchDetail(
                match_id=match_id,
                raw_payload=payload,
                fetched_at=datetime.utcnow(),
            )
            self.db.add(row)
        else:
            row.raw_payload = payload
            row.fetched_at = datetime.utcnow()
        self.db.commit()
