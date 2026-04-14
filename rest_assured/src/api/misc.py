from fastapi import APIRouter

from rest_assured.src.schemas.misc_schema import HelthCheckSchema

misc_router = APIRouter()


@misc_router.get("/health")
def health() -> HelthCheckSchema:
    return HelthCheckSchema(status="ok")
