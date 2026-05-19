from pydantic import BaseModel


class MetricsConfig(BaseModel):
    cache_ttl_seconds: int = 5
