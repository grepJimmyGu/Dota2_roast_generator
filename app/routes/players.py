from fastapi import APIRouter, HTTPException, Query

from dota_core.api.schemas import PlayerOverviewResponse, PlayerSearchResult, CritiqueResponse, RefreshResponse
from dota_core.ingest.player_fetch import search_players
from app.services.player_service import get_player_overview, refresh_player
from app.services.critique_service import generate_player_critique, CritiqueError
from app.errors import PlayerNotFoundError, StratzAPIError

router = APIRouter(tags=["players"])


@router.get("/search", response_model=list[PlayerSearchResult])
def player_search(q: str = Query(..., min_length=2, description="Player name to search")):
    try:
        return search_players(q)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Search unavailable") from exc


@router.get("/{steam_id}/overview", response_model=PlayerOverviewResponse)
def player_overview(steam_id: int, lang: str = Query("en", description="Language: en or zh")):
    try:
        return get_player_overview(steam_id, lang=lang)
    except PlayerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except StratzAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/{steam_id}/roast", response_model=CritiqueResponse)
def player_roast(steam_id: int, lang: str = Query("zh", description="Language: zh or en")):
    try:
        result = generate_player_critique(steam_id, language=lang)
        return CritiqueResponse(
            title=result.title,
            primary_role=result.primary_role,
            overall_verdict=result.overall_verdict,
            critique=result.critique,
            key_problem_tags=result.key_problem_tags,
            evidence_used=[{"match_id": str(e.get("match_id", "")), "reason": e.get("reason", "")}
                           for e in result.evidence_used],
            final_punchline=result.final_punchline,
            tone=result.tone,
        )
    except CritiqueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Critique generation failed") from exc


@router.post("/{steam_id}/refresh", response_model=RefreshResponse)
def refresh(steam_id: int):
    # TODO: move to a background worker — full refresh (100 matches) is 60–120s
    try:
        result = refresh_player(steam_id)
        return RefreshResponse(status="refreshed", matchCount=result["match_count"])
    except StratzAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal server error") from exc
