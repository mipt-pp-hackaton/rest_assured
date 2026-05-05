"""Классификация HTTP-ответов."""


def evaluate_response(
        status_code: int | None = None,
        error_message: str | None = None,
) -> bool:
    """
    Определяет доступность сервиса по HTTP-ответу.

    Сервис НЕ доступен если:
    - status_code >= 500 (ошибка сервера)
    - status_code is None (таймаут/сетевая ошибка)
    - error_message не пустой

    Сервис доступен если:
    - 200 <= status_code < 500
    """
    if error_message:
        return False
    if status_code is None:
        return False
    if status_code >= 500:
        return False
    return 200 <= status_code < 500