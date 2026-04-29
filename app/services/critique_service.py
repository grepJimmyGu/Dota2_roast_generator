"""
Critique service — loads last 10 scored matches from DB, builds context,
calls OpenAI, and returns a LongformCritiqueOutput.
"""
from __future__ import annotations
import json
import logging

from openai import OpenAI

from dota_core.config import OPENAI_API_KEY
from dota_core.roast.models import PlayerMatchStats, LongformCritiqueOutput
from dota_core.roast.longform_context_builder import build_longform_critique_context
from dota_core.roast.longform_prompt_builder import build_longform_critique_prompt
from dota_core.roast.tag_engine import run_tag_rules, player_stats_to_dict
from app.db.session import get_session
from app.repositories.match_repo import MatchRepository
from app.repositories.score_repo import ScoreRepository
from app.repositories.player_repo import PlayerRepository

_log = logging.getLogger("dota.backend")

_CRITIQUE_MATCH_COUNT = 10
_MODEL                = "gpt-5.5"


class CritiqueError(Exception):
    pass


def generate_player_critique(steam_id: int, language: str = "zh") -> LongformCritiqueOutput:
    """
    Generate a long-form critique for the player's last 10 scored matches.

    Raises CritiqueError on missing API key, insufficient data, or API failure.
    """
    if not OPENAI_API_KEY:
        raise CritiqueError(
            "OPENAI_API_KEY not configured — add it to .env to enable the roast feature."
        )

    _log.info(f"[critique] steam_id={steam_id} start")

    with get_session() as db:
        pr = PlayerRepository(db)
        mr = MatchRepository(db)
        sr = ScoreRepository(db)

        player   = pr.get(steam_id)
        matches  = mr.get_for_player(steam_id, limit=_CRITIQUE_MATCH_COUNT)
        score_map = {s.match_id: s for s in sr.get_for_player(steam_id, limit=_CRITIQUE_MATCH_COUNT)}

        if not matches:
            raise CritiqueError("No matches found. Analyze a player first.")

        scored_matches = [m for m in matches if m.match_id in score_map]
        if len(scored_matches) < 3:
            raise CritiqueError(
                f"Only {len(scored_matches)} scored match(es) found — need at least 3 for a meaningful critique."
            )

        stats_list: list[PlayerMatchStats] = []
        for match in scored_matches:
            score  = score_map[match.match_id]
            detail = mr.get_detail(match.match_id) or {}
            raw_stats = detail.get("stats") or {}

            def _sum(arr):
                return float(sum(arr)) if isinstance(arr, list) and arr else None

            dur_min = (match.duration_seconds or 0) / 60 or 1
            gold    = _sum(raw_stats.get("goldPerMinute"))

            stats_list.append(PlayerMatchStats(
                match_id=match.match_id,
                hero_id=match.hero_id or 0,
                hero_name=match.hero_name,
                position=match.position or 1,
                won=match.won,
                duration_min=round((match.duration_seconds or 0) / 60, 1),
                kills=match.kills,
                deaths=match.deaths,
                assists=match.assists,
                overall_score=score.overall_position_score,
                position_score=score.overall_position_score,
                hero_score=score.overall_hero_score,
                early_position_score=score.early_game_position_score,
                mid_position_score=score.mid_game_position_score,
                late_position_score=score.late_game_position_score,
                weaknesses=score.top_weaknesses or [],
                strengths=score.top_strengths  or [],
                hero_damage =_sum(raw_stats.get("heroDamagePerMinute")),
                tower_damage=_sum(raw_stats.get("towerDamagePerMinute")),
                net_worth   =_sum(raw_stats.get("networthPerMinute")),
                gold_per_min=round(gold / dur_min, 1) if gold else None,
                last_hits   =_sum(raw_stats.get("lastHitsPerMinute")),
            ))

    # Run tag engine — roast_tags only; scoring weaknesses/strengths are untouched
    for stats in stats_list:
        stats.roast_tags = run_tag_rules(player_stats_to_dict(stats))

    player_profile = {
        "playerName": player.player_name if player else None,
        "steamId":    steam_id,
    }

    context        = build_longform_critique_context(stats_list, player_profile)
    system_prompt, user_prompt = build_longform_critique_prompt(context, language)

    _log.info(f"[critique] steam_id={steam_id} calling OpenAI model={_MODEL}")

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=_MODEL,
            max_completion_tokens=2048,
            response_format={"type": "json_object"},  # guarantees JSON output
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        )
        raw = response.choices[0].message.content or ""
    except Exception as exc:
        _log.warning(f"[critique] steam_id={steam_id} openai_failed error={type(exc).__name__} detail={exc}")
        raise CritiqueError(f"OpenAI API error: {type(exc).__name__}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        _log.warning(f"[critique] steam_id={steam_id} json_parse_failed")
        raise CritiqueError("Critique generation failed — could not parse response.")

    _log.info(f"[critique] steam_id={steam_id} done tone={parsed.get('tone')}")

    return LongformCritiqueOutput(
        title=parsed.get("title", ""),
        primary_role=parsed.get("primary_role", context.get("primary_role", "")),
        overall_verdict=parsed.get("overall_verdict", ""),
        critique=parsed.get("critique", ""),
        key_problem_tags=parsed.get("key_problem_tags", []),
        evidence_used=parsed.get("evidence_used", []),
        final_punchline=parsed.get("final_punchline", ""),
        tone=parsed.get("tone", "medium"),
    )
