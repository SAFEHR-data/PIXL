from fastapi import APIRouter, HTTPException, status
from .models import TokenRefreshUpdate, AppState


state = AppState()
router = APIRouter()


@router.get("/heart-beat", summary="Health Check")
async def heart_beat() -> str:
    return "OK"


@router.post(
    "/token-bucket-refresh-rate", summary="Update the refresh rate in items per second"
)
async def update_tb_refresh_rate(item: TokenRefreshUpdate) -> str:

    if not isinstance(item.rate, float) or item.rate < 0:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=f"Refresh rate mush be a positive integer. Had {item.rate}",
        )

    state.token_bucket.rate = float(item.rate)
    return "Successfully updated the refresh rate"


@router.get(
    "/token-bucket-refresh-rate", summary="Get the refresh rate in items per second",
    response_model=TokenRefreshUpdate,
)
async def get_tb_refresh_rate() -> TokenRefreshUpdate:
    return TokenRefreshUpdate(rate=state.token_bucket.rate)
