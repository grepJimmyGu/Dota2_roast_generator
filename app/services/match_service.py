"""
Match service — fetches and scores a single match for a given player.

Checks the detail cache (DB) before calling Stratz.
Scoring failures are surfaced via isPartial=True rather than a 502 — identity
and result fields are always returned when the detail is available.
"""
from __future__ import annotations
import logging
import time

from dota_core.ingest.match_fetch import get_match_detail

_log = logging.getLogger("dota.backend")


def _ms(t0: float) -> int:
    return round((time.perf_counter() - t0) * 1000)
from dota_core.benchmarks.fetch import get_phase_benchmarks, rank_to_bracket
from dota_core.scoring.score_match import score_match
from dota_core.domain.heroes import hero_name
from dota_core.api.schemas import (
    MatchDetailResponse,
    PhaseBreakdownSchema,
    PhaseScoreSchema,
)
from app.db.session import get_session
from app.repositories.match_repo import MatchRepository
from dota_core.scoring.features import extract_phase_stats
from app.services.scoring_utils import (
    derive_strengths_weaknesses,
    derive_phase_labels,
    generate_match_summary,
    generate_match_narrative,
    generate_phase_narrative,
    generate_biggest_edge,
    generate_biggest_liability,
    generate_improvement_suggestion,
    get_performance_archetype,
    build_score_context,
    generate_match_analysis,
)
from app.errors import MatchNotFoundError, StratzAPIError


def get_match_analysis(match_id: int, steam_id: int, lang: str = "en") -> MatchDetailResponse:
    """
    Fetch and score a single match for a player.
    Checks the detail cache (DB) before calling Stratz.

    Returns a partial response (isPartial=True) when scoring fails rather than
    raising — identity fields (hero, position, result, duration) are always
    present as long as the detail payload is available.

    Raises:
        MatchNotFoundError: if no detail data is available for this match/player.
        StratzAPIError: on unrecoverable network/API failure during detail fetch.
    """
    t0 = time.perf_counter()
    _log.info(f"[match] match_id={match_id} steam_id={steam_id} start")

    with get_session() as db:
        mr = MatchRepository(db)
        detail = mr.get_detail(match_id)
        detail_source = "cache"

        if detail is None:
            detail_source = "stratz"
            try:
                detail = get_match_detail(match_id, steam_id)
            except Exception as exc:
                _log.warning(f"[match] match_id={match_id} steam_id={steam_id} detail_fetch_failed error={type(exc).__name__}")
                raise StratzAPIError(str(exc)) from exc
            if detail:
                mr.upsert_detail(match_id, detail)

    _log.info(f"[match] match_id={match_id} steam_id={steam_id} detail_source={detail_source}")

    if not detail:
        _log.warning(f"[match] match_id={match_id} steam_id={steam_id} not_found")
        raise MatchNotFoundError(f"Match {match_id} not found for steam_id={steam_id}")

    hero_id      = int(detail.get("heroId") or 0)
    position     = int(detail.get("position") or 1)
    duration_sec = int(detail.get("duration_seconds") or 0)
    average_rank = detail.get("average_rank")
    won          = detail.get("won")

    # --- Scoring (non-fatal: failures produce isPartial=True) ---
    scores:               dict = {}
    strengths:            list[str] | None = None
    weaknesses:           list[str] | None = None
    strongest_phase:      str | None = None
    weakest_phase:        str | None = None
    short_summary:        str | None = None
    match_narrative:      str | None = None
    phase_narrative:      dict | None = None
    biggest_edge:         str | None = None
    biggest_liability:    str | None = None
    improvement_suggestion: str | None = None
    phase_stats:          dict | None = None
    is_partial            = False

    try:
        phase_bms = get_phase_benchmarks(
            hero_id=hero_id,
            position=position,
            average_rank=average_rank,
            duration_min=duration_sec // 60,
        )
        # Pass detail as both match_row and player_detail — detail contains the flat
        # match fields (position, heroId, won, duration_seconds) as well as per-minute stats.
        scores = score_match(detail, detail, phase_bms)
        stat_breakdown = scores.pop("_stat_breakdown", {})
        strengths, weaknesses = derive_strengths_weaknesses(stat_breakdown)
        scored_stat_count = sum(len(v) for v in stat_breakdown.values())

        strongest_phase, weakest_phase = derive_phase_labels(
            scores.get("early_game_position_score"),
            scores.get("mid_game_position_score"),
            scores.get("late_game_position_score"),
        )
        short_summary = generate_match_summary(
            strongest_phase=strongest_phase,
            weakest_phase=weakest_phase,
            strengths=strengths,
            weaknesses=weaknesses,
            overall_position_score=scores.get("overall_position_score"),
            is_partial=False,
            scored_stat_count=scored_stat_count,
        )

        # UI v1 — richer content
        match_narrative = generate_match_narrative(
            strongest_phase=strongest_phase,
            weakest_phase=weakest_phase,
            strengths=strengths,
            weaknesses=weaknesses,
            overall_position_score=scores.get("overall_position_score"),
            overall_hero_score=scores.get("overall_hero_score"),
            position=position,
            is_partial=False,
            scored_stat_count=scored_stat_count,
            lang=lang,
        )
        biggest_edge      = generate_biggest_edge(strengths, strongest_phase, stat_breakdown, lang)
        biggest_liability = generate_biggest_liability(weaknesses, weakest_phase, lang)
        improvement_suggestion = generate_improvement_suggestion(weakest_phase, weaknesses, position, lang)

        # Per-phase stats for display
        raw_phase_data = extract_phase_stats(detail, duration_sec, hero_id=hero_id, position=position)
        phase_stats = {
            phase: {
                "netWorth":   round(ps.get("net_worth_gain")  or 0),
                "heroDamage": round(ps.get("damage_dealt")    or 0),
                "towerDamage":round(ps.get("tower_damage")    or 0),
                "lastHits":   round(ps.get("last_hits")       or 0),
                "kills":      round(ps.get("kills_in_phase")  or 0),
                "deaths":     round(ps.get("deaths_in_phase") or 0),
            }
            for phase, ps in raw_phase_data.items()
        }

        # UI v2 — score context + deep match analysis
        match_analysis = generate_match_analysis(
            stat_breakdown=stat_breakdown,
            phase_stats=phase_stats,
            position=position,
            overall_position_score=scores.get("overall_position_score"),
            weakest_phase=weakest_phase,
            is_partial=False,
            scored_stat_count=scored_stat_count,
            lang=lang,
        )

        phase_narrative = {
            phase: generate_phase_narrative(
                phase=phase,
                position_score=scores.get(f"{phase}_position_score"),
                stat_breakdown=stat_breakdown.get(phase, {}),
                lang=lang,
            )
            for phase in ("early_game", "mid_game", "late_game")
        }

        # Partial if any overall score is missing (e.g. benchmark unavailable for a phase)
        is_partial = (
            scores.get("overall_position_score") is None
            or scores.get("overall_hero_score") is None
        )
    except Exception as exc:
        _log.warning(f"[match] match_id={match_id} steam_id={steam_id} scoring_failed error={type(exc).__name__}")
        is_partial = True
        short_summary = generate_match_summary(
            strongest_phase=None, weakest_phase=None,
            strengths=None, weaknesses=None,
            overall_position_score=None, is_partial=True,
        )

    benchmark_ctx = {
        "bracket":  rank_to_bracket(average_rank),
        "position": position,
        "heroId":   hero_id,
    }

    _log.info(f"[match] match_id={match_id} steam_id={steam_id} is_partial={is_partial} duration_ms={_ms(t0)}")

    return MatchDetailResponse(
        matchId=match_id,
        heroId=hero_id,
        heroName=hero_name(hero_id),
        position=position,
        result="win" if won else ("loss" if won is False else None),
        durationMinutes=round(duration_sec / 60, 1),
        overallPositionScore=scores.get("overall_position_score"),
        overallHeroScore=scores.get("overall_hero_score"),
        phaseBreakdown=PhaseBreakdownSchema(
            early_game=PhaseScoreSchema(
                positionScore=scores.get("early_game_position_score"),
                heroScore=scores.get("early_game_hero_score"),
            ),
            mid_game=PhaseScoreSchema(
                positionScore=scores.get("mid_game_position_score"),
                heroScore=scores.get("mid_game_hero_score"),
            ),
            late_game=PhaseScoreSchema(
                positionScore=scores.get("late_game_position_score"),
                heroScore=scores.get("late_game_hero_score"),
            ),
        ),
        gameCloseness=scores.get("game_closeness"),
        strongestPhase=strongest_phase,
        weakestPhase=weakest_phase,
        shortSummary=short_summary,
        topStrengths=strengths,
        topWeaknesses=weaknesses,
        benchmarkContext=benchmark_ctx,
        hasBenchmarkContext=True,
        isPartial=is_partial,
        matchNarrative=match_narrative,
        phaseNarrative=phase_narrative,
        biggestEdge=biggest_edge,
        biggestLiability=biggest_liability,
        improvementSuggestion=improvement_suggestion,
        performanceProfile=get_performance_archetype(position, lang),
        phaseStats=phase_stats,
        scoreContext=build_score_context(scores["overall_position_score"], bracket=rank_to_bracket(average_rank), lang=lang) if scores.get("overall_position_score") is not None else None,
        heroScoreContext=build_score_context(scores["overall_hero_score"], bracket=rank_to_bracket(average_rank), lang=lang) if scores.get("overall_hero_score") is not None else None,
        matchAnalysis=match_analysis,
    )


