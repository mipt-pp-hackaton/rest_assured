from pydantic import BaseModel


class DBConfig(BaseModel):
    name: str
    user: str
    password: str
    host: str
    port: int

    @property
    def dsl(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )
