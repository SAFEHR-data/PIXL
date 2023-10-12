#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from fastapi import APIRouter, HTTPException, status

from .models import AppState, TokenRefreshUpdate

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
