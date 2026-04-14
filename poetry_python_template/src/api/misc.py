from fastapi import APIRouter

from poetry_python_template.src.schemas.misc_schema import HelthCheckSchema

misc_router = APIRouter()


@misc_router.get("/health")
def health() -> HelthCheckSchema:
    return HelthCheckSchema(status="ok")
