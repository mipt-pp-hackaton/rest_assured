from pydantic import BaseModel, EmailStr


class SmtpConfig(BaseModel):
    host: str
    port: int = 1025
    user: str = ""
    password: str = ""
    use_tls: bool = False
    from_email: EmailStr
    from_name: str