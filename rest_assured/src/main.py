import uvicorn
from fastapi import FastAPI

from rest_assured.src.api.misc import misc_router
from rest_assured.src.configs.app.main import settings

api_base_prefix = "/api/"

app = FastAPI(
    title="Template app",
)
app.include_router(misc_router, prefix=f"{api_base_prefix}misc", tags=["misc"])


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app.host,
        port=settings.app.port,
    )
