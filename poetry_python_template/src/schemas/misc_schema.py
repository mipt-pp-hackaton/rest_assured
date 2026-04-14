from pydantic import BaseModel


class HelthCheckSchema(BaseModel):
    status: str
