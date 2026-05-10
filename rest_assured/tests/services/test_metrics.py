from dataclasses import dataclass
from datetime import datetime, timedelta

from src.services.metrics import compute_current_uptime, compute_sla


@dataclass
class FakeCheckResult:
    checked_at: datetime
    is_up: bool


def make_check(base: datetime, seconds: int, is_up: bool) -> FakeCheckResult:
    return FakeCheckResult(
        checked_at=base + timedelta(seconds=seconds),
        is_up=is_up,
    )


def test_sber_example() -> None:
    base = datetime(2026, 1, 1, 16, 1, 40)

    checks = [
        make_check(base, 0, False),
        make_check(base, 10, True),
        make_check(base, 20, True),
        make_check(base, 30, True),
        make_check(base, 40, False),
        make_check(base, 50, True),
        make_check(base, 60, True),
    ]

    assert compute_current_uptime(checks) == 10
    assert compute_sla(checks) == 0.5


def test_empty_list() -> None:
    assert compute_current_uptime([]) == 0
    assert compute_sla([]) == 0.0


def test_all_up() -> None:
    base = datetime(2026, 1, 1, 16, 0, 0)

    checks = [
        make_check(base, 0, True),
        make_check(base, 10, True),
        make_check(base, 20, True),
        make_check(base, 30, True),
        make_check(base, 40, True),
    ]

    assert compute_current_uptime(checks) == 40
    assert compute_sla(checks) == 1.0


def test_all_down() -> None:
    base = datetime(2026, 1, 1, 16, 0, 0)

    checks = [
        make_check(base, 0, False),
        make_check(base, 10, False),
        make_check(base, 20, False),
    ]

    assert compute_current_uptime(checks) == 0
    assert compute_sla(checks) == 0.0


def test_single_up() -> None:
    base = datetime(2026, 1, 1, 16, 0, 0)

    checks = [make_check(base, 0, True)]

    assert compute_current_uptime(checks) == 0
    assert compute_sla(checks) == 1.0
