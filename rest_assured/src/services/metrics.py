from datetime import datetime
from typing import Protocol


class CheckResult(Protocol):
    checked_at: datetime
    is_up: bool


def compute_current_uptime(checks: list[CheckResult]) -> int:
    """Текущий uptime в секундах от последнего фейла до последней проверки."""
    if not checks:
        return 0

    current_uptime = 0
    previous_check = None

    for check in checks:
        if not check.is_up:
            current_uptime = 0
            previous_check = check
            continue

        if previous_check is not None and previous_check.is_up:
            current_uptime += int((check.checked_at - previous_check.checked_at).total_seconds())

        previous_check = check

    return current_uptime


def compute_sla(checks: list[CheckResult]) -> float:
    """SLA = total_uptime / total_monitoring_time, в долях [0.0..1.0]."""
    if not checks:
        return 0.0

    if len(checks) == 1:
        return 1.0 if checks[0].is_up else 0.0

    total_monitoring_time = int((checks[-1].checked_at - checks[0].checked_at).total_seconds())

    if total_monitoring_time <= 0:
        return 0.0

    total_uptime = 0
    previous_check = checks[0]

    for check in checks[1:]:
        if previous_check.is_up and check.is_up:
            total_uptime += int((check.checked_at - previous_check.checked_at).total_seconds())

        previous_check = check

    return total_uptime / total_monitoring_time
