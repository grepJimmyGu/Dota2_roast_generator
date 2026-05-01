from fastapi import APIRouter, HTTPException, Query

from dota_core.api.schemas import MatchDetailResponse
from app.services.match_service import get_match_analysis
from app.errors import MatchNotFoundError, StratzAPIError

router = APIRouter(tags=["matches"])


@router.get("/{match_id}", response_model=MatchDetailResponse)
def match_detail(
    match_id: int,
    steam_id: int = Query(..., description="Steam account ID of the player to analyze"),
    lang: str    = Query("en", description="Language: en or zh"),
):
    try:
        return get_match_analysis(match_id, steam_id, lang=lang)
    except MatchNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except StratzAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal server error") from exc
