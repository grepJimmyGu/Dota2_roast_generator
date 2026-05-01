"""
Player service — orchestrates Stratz ingest, DB persistence, and overview assembly.

Cache policy:
  Case A — fresh cache (age < CACHE_FRESHNESS_HOURS): return from DB, zero Stratz calls.
  Case B — stale cache: return from DB with isStale=True / refreshRecommended=True.
  Case C — no cache: live fetch → persist → return.

POST /refresh always executes a live fetch regardless of staleness.
"""
from __future__ import annotations
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

_log = logging.getLogger("dota.backend")


def _ms(t0: float) -> int:
    """Elapsed milliseconds since perf_counter snapshot t0."""
    return round((time.perf_counter() - t0) * 1000)

from dota_core.ingest.player_fetch import get_player_info, get_ranked_matches
from dota_core.ingest.match_fetch import get_match_detail
from dota_core.benchmarks.fetch import get_phase_benchmarks
from dota_core.scoring.score_match import score_match
from dota_core.domain.heroes import hero_name
from dota_core.config import CACHE_FRESHNESS_HOURS
from dota_core.api.schemas import PlayerOverviewResponse, MatchSummarySchema, DataCompletenessSchema
from app.db.session import get_session
from app.repositories.player_repo import PlayerRepository
from app.repositories.match_repo import MatchRepository
from app.repositories.score_repo import ScoreRepository
from app.services.scoring_utils import (
    derive_strengths_weaknesses,
    derive_phase_labels,
    generate_player_summary,
    generate_player_narrative,
    compute_consistency_rating,
    compute_recurring_patterns,
    get_performance_archetype,
    build_score_context,
    generate_recurring_pattern_entries,
)
from app.errors import PlayerNotFoundError, StratzAPIError

_SCORE_LIVE_N = 10


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_player_overview(steam_id: int, match_count: int = 20, lang: str = "en") -> PlayerOverviewResponse:
    """
    Return a player overview, using the cache when possible.

    Case A: fresh cache → DB only, no Stratz calls.
    Case B: stale cache → DB data returned with isStale=True.
    Case C: no cache    → live fetch, persist, return.
    """
    t0 = time.perf_counter()
    _log.info(f"[overview] steam_id={steam_id} start")

    with get_session() as db:
        pr = PlayerRepository(db)
        player = pr.get(steam_id)

        if player is None:
            _log.info(f"[overview] steam_id={steam_id} cache_hit=False")
            result = _do_live_refresh(steam_id, match_count, db, lang=lang)
            _log.info(f"[overview] steam_id={steam_id} complete duration_ms={_ms(t0)}")
            return result

        is_stale = not _is_fresh(player.last_refreshed_at)
        _log.info(f"[overview] steam_id={steam_id} cache_hit=True is_stale={is_stale}")
        result = _build_cached_overview(steam_id, player, match_count, is_stale=is_stale, db=db, lang=lang)
        _log.info(f"[overview] steam_id={steam_id} complete duration_ms={_ms(t0)}")
        return result


def refresh_player(steam_id: int, match_count: int = 100) -> dict:
    """
    Force a full live refresh for a player, bypassing the freshness window.
    Returns {"match_count": int}.

    TODO: move to an async background worker — full refresh (100 matches) is 60–120s.
          Structure is intentionally simple so wrapping in BackgroundTasks/Celery is straightforward.
    """
    _log.info(f"[refresh] steam_id={steam_id} force=True matches_requested={match_count}")
    with get_session() as db:
        overview = _do_live_refresh(steam_id, match_count, db)
        return {"match_count": overview.recentMatchCount}


# ---------------------------------------------------------------------------
# Cache path (Case A / B)
# ---------------------------------------------------------------------------

def _build_cached_overview(
    steam_id: int,
    player,
    match_count: int,
    is_stale: bool,
    db: Session,
    lang: str = "en",
) -> PlayerOverviewResponse:
    mr = MatchRepository(db)
    sr = ScoreRepository(db)

    matches = mr.get_for_player(steam_id, limit=match_count)
    scores_by_match = {s.match_id: s for s in sr.get_for_player(steam_id, limit=match_count)}

    summaries: list[MatchSummarySchema] = []
    for match in matches:
        score = scores_by_match.get(match.match_id)
        summaries.append(MatchSummarySchema(
            matchId=match.match_id,
            heroId=match.hero_id or 0,
            heroName=match.hero_name,
            position=match.position or 1,
            won=match.won,
            durationMinutes=round((match.duration_seconds or 0) / 60, 1),
            kills=match.kills,
            deaths=match.deaths,
            assists=match.assists,
            overallPositionScore=score.overall_position_score if score else None,
            overallHeroScore=score.overall_hero_score if score else None,
            gameCloseness=score.game_closeness if score else None,
            scoringPending=score is None,
        ))

    scored  = [s for s in summaries if not s.scoringPending]
    pending = [s for s in summaries if s.scoringPending]
    agg = _compute_aggregates(scored)

    # For cached reads, detail availability is proxied by score availability.
    completeness = DataCompletenessSchema(
        requestedMatchCount=len(matches),
        fetchedDetailCount=len(scored),
        scoredMatchCount=len(scored),
        failedMatchCount=len(pending),
    )

    score_rows = list(scores_by_match.values())
    strongest_phase, weakest_phase = _compute_player_phase_labels(score_rows)
    recent_trend = _compute_recent_trend(scored)
    archetype    = _compute_archetype(matches, lang)
    recurring_s, recurring_w = compute_recurring_patterns(score_rows)
    consistency  = compute_consistency_rating([s.overallPositionScore for s in scored if s.overallPositionScore is not None])
    short_summary = generate_player_summary(
        strongest_phase=strongest_phase, weakest_phase=weakest_phase,
        recent_trend=recent_trend, average_overall_score=agg.get("averageOverallScore"),
        match_count=len(matches),
    )
    player_narrative = generate_player_narrative(
        archetype=archetype, strongest_phase=strongest_phase, weakest_phase=weakest_phase,
        recurring_strengths=recurring_s, recurring_weaknesses=recurring_w,
        consistency_rating=consistency, recent_trend=recent_trend,
        average_overall_score=agg.get("averageOverallScore"), match_count=len(matches),
        lang=lang,
    )
    match_records = _build_pattern_records(matches, scores_by_match)
    recurring_patterns = generate_recurring_pattern_entries(match_records, lang=lang)
    avg_score = agg.get("averageOverallScore")

    return PlayerOverviewResponse(
        steamId=steam_id,
        playerName=player.player_name,
        avatarUrl=player.avatar_url,
        rank=player.rank,
        recentMatchCount=len(matches),
        averageOverallScore=avg_score,
        averagePositionScore=agg.get("averagePositionScore"),
        averageHeroScore=agg.get("averageHeroScore"),
        strongestPhase=strongest_phase,
        weakestPhase=weakest_phase,
        shortSummary=short_summary,
        bestHeroes=_compute_best_heroes(scored),
        recentTrend=recent_trend,
        playerNarrative=player_narrative,
        consistencyRating=consistency,
        performanceArchetype=archetype,
        scoreContext=build_score_context(avg_score, lang=lang) if avg_score is not None else None,
        recurringPatterns=recurring_patterns or None,
        isStale=is_stale,
        refreshRecommended=is_stale,
        lastRefreshedAt=player.last_refreshed_at,
        dataCompleteness=completeness,
        recentMatches=summaries,
    )


# ---------------------------------------------------------------------------
# Live fetch path (Case C + POST /refresh)
# ---------------------------------------------------------------------------

def _do_live_refresh(steam_id: int, match_count: int, db: Session, lang: str = "en") -> PlayerOverviewResponse:
    t0 = time.perf_counter()
    pr = PlayerRepository(db)
    mr = MatchRepository(db)
    sr = ScoreRepository(db)

    _log.info(f"[refresh] steam_id={steam_id} start matches_requested={match_count}")
    pr.set_refresh_started(steam_id)

    # --- Fetch player profile ---
    try:
        info = get_player_info(steam_id)
    except Exception as exc:
        pr.set_refresh_error(steam_id, str(exc))
        _log.warning(f"[refresh] steam_id={steam_id} player_fetch_failed error={type(exc).__name__}")
        raise StratzAPIError(str(exc)) from exc

    if not info:
        pr.set_refresh_error(steam_id, "Player not found in Stratz")
        _log.warning(f"[refresh] steam_id={steam_id} player_not_found")
        raise PlayerNotFoundError(f"No Stratz data for steam_id={steam_id}")

    steam_account = info.get("steamAccount") or {}
    player = pr.upsert(
        steam_id,
        player_name=steam_account.get("name"),
        avatar_url=steam_account.get("avatar"),
    )

    # --- Fetch match list ---
    try:
        df = get_ranked_matches(steam_id, total=match_count)
    except Exception as exc:
        pr.set_refresh_error(steam_id, str(exc))
        _log.warning(f"[refresh] steam_id={steam_id} match_list_failed error={type(exc).__name__}")
        raise StratzAPIError(str(exc)) from exc

    _log.info(f"[refresh] steam_id={steam_id} matches_fetched={len(df)}")

    if df.empty:
        pr.set_refresh_ok(steam_id)
        player = pr.get(steam_id)
        _log.info(f"[refresh] steam_id={steam_id} complete no_matches duration_ms={_ms(t0)}")
        return PlayerOverviewResponse(
            steamId=steam_id,
            playerName=player.player_name,
            avatarUrl=player.avatar_url,
            recentMatchCount=0,
            isStale=False,
            refreshRecommended=False,
            lastRefreshedAt=player.last_refreshed_at,
            dataCompleteness=DataCompletenessSchema(
                requestedMatchCount=0,
                fetchedDetailCount=0,
                scoredMatchCount=0,
                failedMatchCount=0,
            ),
        )

    # --- Persist match rows ---
    mr.upsert_many([_df_row_to_match_dict(steam_id, row.to_dict()) for _, row in df.iterrows()])

    # --- Score first N matches, mark rest as pending; track per-match outcomes ---
    summaries:          list[MatchSummarySchema] = []
    detail_fetch_count  = 0
    scored_count        = 0
    fail_count          = 0

    for idx, (_, row) in enumerate(df.iterrows()):
        row_dict     = row.to_dict()
        match_id     = int(row_dict["match_id"])
        hero_id      = _safe_int(row_dict.get("heroId"))  or 0
        position     = _safe_int(row_dict.get("position")) or 1
        duration_sec = _safe_int(row_dict.get("duration_seconds")) or 0

        if idx < _SCORE_LIVE_N:
            summary, detail_ok, score_ok = _score_persist_and_summarize(
                match_id, row_dict, steam_id, hero_id, position, duration_sec, mr, sr,
            )
            if detail_ok:
                detail_fetch_count += 1
            if score_ok:
                scored_count += 1
            else:
                fail_count += 1
        else:
            summary = MatchSummarySchema(
                matchId=match_id,
                heroId=hero_id,
                heroName=hero_name(hero_id),
                position=position,
                won=row_dict.get("won"),
                durationMinutes=round(duration_sec / 60, 1),
                kills=row_dict.get("kills"),
                deaths=row_dict.get("deaths"),
                assists=row_dict.get("assists"),
                scoringPending=True,
            )
        summaries.append(summary)

    _log.info(
        f"[refresh] steam_id={steam_id} "
        f"details_fetched={detail_fetch_count} scored={scored_count} failed={fail_count}"
    )

    pr.set_refresh_ok(steam_id)
    player = pr.get(steam_id)
    _log.info(f"[refresh] steam_id={steam_id} complete duration_ms={_ms(t0)}")

    scored = [s for s in summaries[:_SCORE_LIVE_N] if not s.scoringPending]
    agg = _compute_aggregates(scored)

    completeness = DataCompletenessSchema(
        requestedMatchCount=len(df),
        fetchedDetailCount=detail_fetch_count,
        scoredMatchCount=scored_count,
        failedMatchCount=fail_count,
    )

    all_scores  = sr.get_for_player(steam_id, limit=match_count)
    matches_orm = mr.get_for_player(steam_id, limit=match_count)
    scores_by_match_all = {s.match_id: s for s in all_scores}
    strongest_phase, weakest_phase = _compute_player_phase_labels(all_scores)
    recent_trend = _compute_recent_trend(scored)
    archetype    = _compute_archetype(matches_orm, lang)
    recurring_s, recurring_w = compute_recurring_patterns(all_scores)
    consistency  = compute_consistency_rating([s.overallPositionScore for s in scored if s.overallPositionScore is not None])
    short_summary = generate_player_summary(
        strongest_phase=strongest_phase, weakest_phase=weakest_phase,
        recent_trend=recent_trend, average_overall_score=agg.get("averageOverallScore"),
        match_count=len(df),
    )
    player_narrative = generate_player_narrative(
        archetype=archetype, strongest_phase=strongest_phase, weakest_phase=weakest_phase,
        recurring_strengths=recurring_s, recurring_weaknesses=recurring_w,
        consistency_rating=consistency, recent_trend=recent_trend,
        average_overall_score=agg.get("averageOverallScore"), match_count=len(df),
        lang=lang,
    )
    match_records = _build_pattern_records(matches_orm, scores_by_match_all)
    recurring_patterns = generate_recurring_pattern_entries(match_records, lang=lang)
    avg_score = agg.get("averageOverallScore")

    return PlayerOverviewResponse(
        steamId=steam_id,
        playerName=player.player_name,
        avatarUrl=player.avatar_url,
        rank=player.rank,
        recentMatchCount=len(df),
        averageOverallScore=avg_score,
        averagePositionScore=agg.get("averagePositionScore"),
        averageHeroScore=agg.get("averageHeroScore"),
        strongestPhase=strongest_phase,
        weakestPhase=weakest_phase,
        shortSummary=short_summary,
        bestHeroes=_compute_best_heroes(scored),
        recentTrend=recent_trend,
        playerNarrative=player_narrative,
        consistencyRating=consistency,
        performanceArchetype=archetype,
        scoreContext=build_score_context(avg_score, lang=lang) if avg_score is not None else None,
        recurringPatterns=recurring_patterns or None,
        isStale=False,
        refreshRecommended=False,
        lastRefreshedAt=player.last_refreshed_at,
        dataCompleteness=completeness,
        recentMatches=summaries,
    )


def _score_persist_and_summarize(
    match_id: int,
    row_dict: dict,
    steam_id: int,
    hero_id: int,
    position: int,
    duration_sec: int,
    mr: MatchRepository,
    sr: ScoreRepository,
) -> tuple[MatchSummarySchema, bool, bool]:
    """
    Score one match, persist detail and scores, return (summary, detail_ok, scored_ok).

    Never raises — on any failure returns the pending summary with False outcome flags.
    Partial failures (detail fetched but scoring failed) are captured in the flags.
    """
    pending = MatchSummarySchema(
        matchId=match_id,
        heroId=hero_id,
        heroName=hero_name(hero_id),
        position=position,
        won=row_dict.get("won"),
        durationMinutes=round(duration_sec / 60, 1),
        kills=row_dict.get("kills"),
        deaths=row_dict.get("deaths"),
        assists=row_dict.get("assists"),
        scoringPending=True,
    )

    detail_ok = False
    try:
        # Check detail cache first; fetch and persist only on a cache miss.
        detail = mr.get_detail(match_id)
        if detail is None:
            detail = get_match_detail(match_id, steam_id)
            if detail:
                mr.upsert_detail(match_id, detail)

        if not detail or not detail.get("stats"):
            return pending, False, False

        detail_ok = True

        phase_bms = get_phase_benchmarks(
            hero_id=hero_id,
            position=position,
            average_rank=row_dict.get("average_rank"),
            duration_min=duration_sec // 60,
        )
        scores = score_match(row_dict, detail, phase_bms)
        stat_breakdown = scores.pop("_stat_breakdown", {})
        strengths, weaknesses = derive_strengths_weaknesses(stat_breakdown)

        sr.upsert(match_id, steam_id, scores, top_strengths=strengths, top_weaknesses=weaknesses)

        return (
            MatchSummarySchema(
                matchId=match_id,
                heroId=hero_id,
                heroName=hero_name(hero_id),
                position=position,
                won=row_dict.get("won"),
                durationMinutes=round(duration_sec / 60, 1),
                kills=row_dict.get("kills"),
                deaths=row_dict.get("deaths"),
                assists=row_dict.get("assists"),
                overallPositionScore=scores.get("overall_position_score"),
                overallHeroScore=scores.get("overall_hero_score"),
                gameCloseness=scores.get("game_closeness"),
                scoringPending=False,
            ),
            True,
            True,
        )
    except Exception as exc:
        _log.warning(
            f"[refresh] steam_id={steam_id} match_id={match_id} "
            f"scoring_failed detail_ok={detail_ok} error={type(exc).__name__}"
        )
        return pending, detail_ok, False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_fresh(last_refreshed_at: datetime | None) -> bool:
    if last_refreshed_at is None:
        return False
    return datetime.utcnow() - last_refreshed_at < timedelta(hours=CACHE_FRESHNESS_HOURS)


def _safe_int(val) -> int | None:
    """Convert val to int, returning None for NaN, None, or unconvertible values."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if (f != f) else int(f)   # f != f is True only for NaN
    except (TypeError, ValueError):
        return None


def _df_row_to_match_dict(steam_id: int, row: dict) -> dict:
    """Convert a DataFrame row from get_ranked_matches() to a Match model dict."""
    hero_id = _safe_int(row.get("heroId"))
    return {
        "match_id":         int(row["match_id"]),
        "steam_id":         steam_id,
        "hero_id":          hero_id,
        "hero_name":        hero_name(hero_id) if hero_id else None,
        "position":         _safe_int(row.get("position")),
        "start_time":       _safe_int(row.get("start_time")),
        "duration_seconds": _safe_int(row.get("duration_seconds")),
        "won":              row.get("won"),
        "kills":            _safe_int(row.get("kills")),
        "deaths":           _safe_int(row.get("deaths")),
        "assists":          _safe_int(row.get("assists")),
        "average_rank":     _safe_int(row.get("average_rank")),
        "radiant_kills":    _safe_int(row.get("radiant_kills")),
        "dire_kills":       _safe_int(row.get("dire_kills")),
    }


def _compute_aggregates(scored: list[MatchSummarySchema]) -> dict:
    if not scored:
        return {}

    pos_scores  = [s.overallPositionScore for s in scored if s.overallPositionScore is not None]
    hero_scores = [s.overallHeroScore     for s in scored if s.overallHeroScore     is not None]
    both = [
        (p + h) / 2
        for s in scored
        for p, h in [(s.overallPositionScore, s.overallHeroScore)]
        if p is not None and h is not None
    ]

    result: dict = {}
    if both:
        result["averageOverallScore"]  = round(sum(both) / len(both), 2)
    if pos_scores:
        result["averagePositionScore"] = round(sum(pos_scores) / len(pos_scores), 2)
    if hero_scores:
        result["averageHeroScore"]     = round(sum(hero_scores) / len(hero_scores), 2)
    return result


def _compute_best_heroes(scored: list[MatchSummarySchema]) -> list[dict] | None:
    hero_score_map: dict[int, list[float]] = defaultdict(list)
    for s in scored:
        if s.heroId and s.overallHeroScore is not None:
            hero_score_map[s.heroId].append(s.overallHeroScore)

    ranked = sorted(
        [
            {
                "heroId":   hid,
                "heroName": hero_name(hid),
                "avgScore": round(sum(scores) / len(scores), 2),
                "games":    len(scores),
            }
            for hid, scores in hero_score_map.items()
            if len(scores) >= 2
        ],
        key=lambda x: x["avgScore"],
        reverse=True,
    )
    return ranked[:3] or None


def _build_pattern_records(matches, scores_by_match: dict) -> list[dict]:
    """Build flat dicts for generate_recurring_pattern_entries from ORM objects."""
    records = []
    for m in matches:
        score = scores_by_match.get(m.match_id)
        if not score:
            continue
        records.append({
            "match_id":      m.match_id,
            "hero_name":     m.hero_name,
            "won":           m.won,
            "overall_score": score.overall_position_score,
            "strengths":     score.top_strengths  or [],
            "weaknesses":    score.top_weaknesses or [],
        })
    return records


def _compute_archetype(matches, lang: str = "en") -> str | None:
    """Return the position-based archetype label for the most-played position."""
    from collections import Counter
    counts = Counter(m.position for m in matches if m.position)
    if not counts:
        return None
    dominant = counts.most_common(1)[0][0]
    return get_performance_archetype(dominant, lang)


def _compute_player_phase_labels(score_rows) -> tuple[str | None, str | None]:
    """
    Average per-phase position scores across all MatchScore rows and return
    (strongest_phase, weakest_phase) labels via derive_phase_labels().
    """
    early_vals, mid_vals, late_vals = [], [], []
    for s in score_rows:
        if s.early_game_position_score is not None:
            early_vals.append(s.early_game_position_score)
        if s.mid_game_position_score is not None:
            mid_vals.append(s.mid_game_position_score)
        if s.late_game_position_score is not None:
            late_vals.append(s.late_game_position_score)

    avg = lambda vals: sum(vals) / len(vals) if vals else None
    return derive_phase_labels(avg(early_vals), avg(mid_vals), avg(late_vals))


def _compute_recent_trend(scored: list[MatchSummarySchema]) -> str | None:
    scores = [s.overallHeroScore for s in scored if s.overallHeroScore is not None]
    if len(scores) < 4:
        return None
    mid = len(scores) // 2
    avg_first  = sum(scores[:mid]) / mid
    avg_second = sum(scores[mid:]) / (len(scores) - mid)
    delta = avg_second - avg_first
    if delta > 5:
        return "improving"
    if delta < -5:
        return "declining"
    return "stable"
