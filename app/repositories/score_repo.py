"""
ScoreRepository — store and load per-match scoring results.
"""
from __future__ import annotations
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import MatchScore

# Score keys from score_match() that map directly to MatchScore columns.
_SCORE_FIELDS = frozenset({
    "overall_position_score",
    "overall_hero_score",
    "early_game_position_score",
    "early_game_hero_score",
    "mid_game_position_score",
    "mid_game_hero_score",
    "late_game_position_score",
    "late_game_hero_score",
    "game_closeness",
})


class ScoreRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, match_id: int) -> MatchScore | None:
        return self.db.get(MatchScore, match_id)

    def get_for_player(self, steam_id: int, limit: int = 20) -> list[MatchScore]:
        """Return up to `limit` scored matches for a player, most recently scored first."""
        return (
            self.db.query(MatchScore)
            .filter(MatchScore.steam_id == steam_id)
            .order_by(MatchScore.scored_at.desc())
            .limit(limit)
            .all()
        )

    def upsert(
        self,
        match_id: int,
        steam_id: int,
        scores: dict,
        top_strengths: list[str] | None = None,
        top_weaknesses: list[str] | None = None,
    ) -> MatchScore:
        """
        Insert or update a MatchScore row.

        `scores` is the raw dict returned by score_match(). Keys prefixed with '_'
        (e.g. _stat_breakdown) are ignored — they are internal to the scoring engine.
        """
        row = self.db.get(MatchScore, match_id)
        if row is None:
            row = MatchScore(match_id=match_id, steam_id=steam_id)
            self.db.add(row)

        for field in _SCORE_FIELDS:
            setattr(row, field, scores.get(field))

        row.top_strengths  = top_strengths
        row.top_weaknesses = top_weaknesses
        row.scored_at      = datetime.utcnow()

        self.db.commit()
        self.db.refresh(row)
        return row
