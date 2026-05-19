from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/health", tags=["scheduler"])


@router.get("/scheduler")
async def health_scheduler(request: Request):
    return request.app.state.runner.stats
