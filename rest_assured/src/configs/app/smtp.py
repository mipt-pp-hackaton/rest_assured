from pydantic import BaseModel, EmailStr, SecretStr


class SmtpConfig(BaseModel):
    host: str
    port: int = 1025
    user: str = ""
    password: SecretStr = SecretStr("")
    use_tls: bool = False
    from_email: EmailStr
    from_name: str
