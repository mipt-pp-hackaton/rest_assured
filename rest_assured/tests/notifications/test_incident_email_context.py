"""Регресс-тесты: контекст инцидент-писем должен заполнять поля шаблонов.

Раньше incidents.py клал в контекст объекты (incident/check), а шаблоны ждали
плоские ключи (opened_at/last_error/...) — поля рендерились пустыми. Эти тесты
прогоняют РЕАЛЬНЫЕ шаблоны через билдеры контекста и проверяют, что динамика
действительно попадает в письмо.
"""

from datetime import datetime, timezone

from rest_assured.src.models.checks import CheckResult
from rest_assured.src.models.incidents import Incident
from rest_assured.src.models.services import Service
from rest_assured.src.services.incidents import (
    _incident_closed_context,
    _incident_opened_context,
    _incident_reminder_context,
    _sla_breach_context,
)
from rest_assured.src.services.notifications.email import _render

_OPENED = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
_CLOSED = datetime(2026, 6, 1, 13, 30, 0, tzinfo=timezone.utc)


def _service(**kw) -> Service:
    return Service(name="svc", url="http://example.com", **kw)


def _render_all(kind: str, ctx: dict) -> str:
    return "\n".join(
        _render(f"{kind}.{ext}", ctx) for ext in ("subject.j2", "txt.j2", "html.j2")
    )


def test_incident_opened_context_fills_date_and_error():
    inc = Incident(service_id=1, opened_at=_OPENED, last_error="boom")
    chk = CheckResult(
        service_id=1, is_up=False, http_status=500, error="HTTP 500", checked_at=_OPENED
    )

    ctx = _incident_opened_context(_service(), inc, chk)
    assert ctx["opened_at"] == "2026-06-01 12:00:00 UTC"

    body = _render_all("incident_opened", ctx)
    assert "2026-06-01 12:00:00 UTC" in body
    assert "HTTP 500" in body


def test_incident_reminder_context_fills_date_and_error():
    inc = Incident(service_id=1, opened_at=_OPENED, last_error="still down")
    chk = CheckResult(service_id=1, is_up=False, error="still down", checked_at=_CLOSED)

    ctx = _incident_reminder_context(_service(), inc, chk)
    body = _render_all("incident_reminder", ctx)
    assert "2026-06-01 12:00:00 UTC" in body
    assert "still down" in body


def test_incident_closed_context_fills_date_and_duration():
    inc = Incident(service_id=1, opened_at=_OPENED)

    ctx = _incident_closed_context(_service(), inc, _CLOSED)
    assert ctx["closed_at"] == "2026-06-01 13:30:00 UTC"
    assert ctx["duration"] == "1:30:00"

    body = _render_all("incident_closed", ctx)
    assert "2026-06-01 13:30:00 UTC" in body
    assert "1:30:00" in body


def test_sla_breach_context_fills_target_and_actual():
    ctx = _sla_breach_context(_service(sla_target_pct=99.9), sla_actual=97.531)
    assert ctx["sla_target"] == 99.9
    assert ctx["sla_actual"] == 97.53

    body = _render_all("sla_breach", ctx)
    assert "99.9" in body
    assert "97.53" in body
