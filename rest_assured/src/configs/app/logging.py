from pydantic import BaseModel


class LoggingConfig(BaseModel):
    """Настройки логирования.

    ``json_logs`` управляет структурированным JSON-выводом (loguru ``serialize``)
    с перенаправлением stdlib-логов (планировщик, uvicorn) в loguru — пригодно для
    сбора в ELK / Loki / Datadog. **Включено по умолчанию**; отключить можно через
    ``DYNACONF_LOGGING__JSON_LOGS=false`` (или для локальной отладки человекочитаемых
    логов). Под pytest перехват не применяется, чтобы не ломать ``caplog``.
    """

    json_logs: bool = True
    level: str = "INFO"
