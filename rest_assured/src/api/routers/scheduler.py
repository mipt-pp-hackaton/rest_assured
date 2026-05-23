from fastapi import APIRouter, Depends, Request

from rest_assured.src.services.auth.dependencies import get_current_active_user

router = APIRouter(
    prefix="/api/health",
    tags=["scheduler"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("/scheduler")
async def health_scheduler(request: Request):
    return request.app.state.runner.stats
