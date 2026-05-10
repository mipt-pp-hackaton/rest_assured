from pydantic import BaseModel, SecretStr


class DBConfig(BaseModel):
    name: str
    user: str
    password: SecretStr
    host: str
    port: int

    @property
    def dsl(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.name}"
        )
