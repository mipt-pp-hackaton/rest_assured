"""Unit tests for EmailSender template rendering."""

import pytest

from rest_assured.src.notifications.email import _render


@pytest.mark.parametrize(
    "kind, context",
    [
        (
            "incident_opened",
            {
                "service": {"name": "TestSvc", "url": "http://test.com"},
                "opened_at": "2026-01-01 12:00",
                "last_error": "Timeout",
            },
        ),
        (
            "incident_closed",
            {
                "service": {"name": "TestSvc", "url": "http://test.com"},
                "closed_at": "2026-01-01 13:00",
                "duration": "1 hour",
            },
        ),
        (
            "incident_reminder",
            {
                "service": {"name": "TestSvc", "url": "http://test.com"},
                "opened_at": "2026-01-01 12:00",
                "last_error": "Timeout",
            },
        ),
        (
            "sla_breach",
            {
                "service": {"name": "TestSvc", "url": "http://test.com"},
                "sla_target": 99.9,
                "sla_actual": 97.5,
            },
        ),
    ],
)
def test_render_subject_and_bodies(kind, context):
    subject = _render(f"{kind}.subject.j2", context).strip()
    text_body = _render(f"{kind}.txt.j2", context)
    html_body = _render(f"{kind}.html.j2", context)

    assert len(subject) > 0
    assert len(text_body) > 0
    assert len(html_body) > 0
    assert "{{" not in subject
    assert "{{" not in text_body
    assert "{{" not in html_body


def test_unknown_kind_raises_template_not_found():
    with pytest.raises(Exception):
        _render("unknown.subject.j2", {})
