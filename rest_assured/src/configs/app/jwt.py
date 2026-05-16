from pydantic import BaseModel


class JWTConfig(BaseModel):
    secret: str
    ttl_hours: int = 24
    algorithm: str = "HS256"
