"""
PlayerRepository — read/write player profile and refresh metadata.
All methods operate on an externally provided Session; callers own commit/rollback.
"""
from __future__ import annotations
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import Player


class PlayerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, steam_id: int) -> Player | None:
        return self.db.get(Player, steam_id)

    def upsert(self, steam_id: int, **fields) -> Player:
        """Insert or update a player row. Returns the persisted Player."""
        player = self.db.get(Player, steam_id)
        if player is None:
            player = Player(steam_id=steam_id, **fields)
            self.db.add(player)
        else:
            for key, val in fields.items():
                setattr(player, key, val)
        self.db.commit()
        self.db.refresh(player)
        return player

    def set_refresh_started(self, steam_id: int) -> None:
        """Mark refresh as in-progress before a live fetch begins."""
        player = self._get_or_create(steam_id)
        player.last_attempted_at = datetime.utcnow()
        player.refresh_status = "pending"
        player.error_message = None
        self.db.commit()

    def set_refresh_ok(self, steam_id: int) -> None:
        """Mark refresh as successful after all data is persisted."""
        player = self._get_or_create(steam_id)
        now = datetime.utcnow()
        player.last_attempted_at = now
        player.last_refreshed_at = now
        player.refresh_status = "ok"
        player.error_message = None
        self.db.commit()

    def set_refresh_error(self, steam_id: int, error_message: str) -> None:
        """Record a failed refresh attempt."""
        player = self._get_or_create(steam_id)
        player.last_attempted_at = datetime.utcnow()
        player.refresh_status = "error"
        player.error_message = error_message[:1024]   # cap length
        self.db.commit()

    def _get_or_create(self, steam_id: int) -> Player:
        player = self.db.get(Player, steam_id)
        if player is None:
            player = Player(steam_id=steam_id)
            self.db.add(player)
            self.db.flush()
        return player
