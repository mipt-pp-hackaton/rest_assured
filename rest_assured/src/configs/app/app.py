from pydantic import BaseModel


class APPConfig(BaseModel):
    host: str
    port: int
    use_testcontainers: bool = False
