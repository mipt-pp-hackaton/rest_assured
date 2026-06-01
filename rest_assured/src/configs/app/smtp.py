from pydantic import BaseModel, EmailStr, SecretStr


class SmtpConfig(BaseModel):
    host: str
    port: int = 1025
    user: str = ""
    password: SecretStr = SecretStr("")
    # use_tls — implicit TLS (SMTPS, обычно порт 465). Для Yandex/Gmail: True + port 465.
    use_tls: bool = False
    # start_tls — STARTTLS-апгрейд на plaintext-соединении (обычно порт 587).
    # None = аиосмтп решает сам (оппортунистический STARTTLS, если сервер поддерживает);
    # True = требовать STARTTLS; False = запретить. Несовместимо с use_tls=True.
    start_tls: bool | None = None
    # validate_certs — проверка TLS-сертификата сервера (отключать только для self-signed).
    validate_certs: bool = True
    # timeout_seconds — таймаут операций SMTP.
    timeout_seconds: int = 30
    from_email: EmailStr
    from_name: str
