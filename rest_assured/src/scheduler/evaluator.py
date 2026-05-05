import httpx


def evaluate_response(response: httpx.Response | None, error: Exception | None = None) -> dict:
    """
    Классифицирует HTTP-ответ и возвращает словарь с результатом проверки.

    Args:
        response: ответ от httpx (может быть None при ошибке соединения)
        error: исключение, если запрос не удался

    Returns:
        dict с ключами: is_up, status_code, response_time_ms, error_message
    """
    if error is not None:
        return {
            "is_up": False,
            "status_code": None,
            "response_time_ms": None,
            "error_message": str(error),
        }

    if response is None:
        return {
            "is_up": False,
            "status_code": None,
            "response_time_ms": None,
            "error_message": "No response received",
        }

    is_up = response.status_code < 500

    return {
        "is_up": is_up,
        "status_code": response.status_code,
        "response_time_ms": int(response.elapsed.total_seconds() * 1000),
        "error_message": None if is_up else f"Server error: {response.status_code}",
    }
