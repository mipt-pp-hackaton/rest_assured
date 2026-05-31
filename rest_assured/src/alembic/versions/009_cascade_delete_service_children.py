"""service deletion cascades: ON DELETE CASCADE on FKs referencing services/incidents

Revision ID: 009
Revises: 008
Create Date: 2026-05-31 00:00:00.000000

Удаление сервиса падало с ForeignKeyViolationError, потому что строки в
``check_results`` / ``incidents`` / ``notification_log`` всё ещё ссылались на
``services.id``. Пересоздаём эти FK (плюс ``notification_log.incident_id`` →
``incidents.id``, чтобы каскад инцидентов не упёрся в лог) с ON DELETE CASCADE:
удаление сервиса теперь убирает и всю его историю проверок, инциденты и записи
лога уведомлений.

Имена констрейнтов — Postgres-дефолты (``<table>_<column>_fkey``), т.к. в
0001/исходных миграциях FK создавались без явного имени.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "009"
down_revision: Union[str, Sequence[str], None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (constraint_name, table, referent_table, local_col, remote_col)
_FKS = [
    ("check_results_service_id_fkey", "check_results", "services", "service_id", "id"),
    ("incidents_service_id_fkey", "incidents", "services", "service_id", "id"),
    ("notification_log_service_id_fkey", "notification_log", "services", "service_id", "id"),
    ("notification_log_incident_id_fkey", "notification_log", "incidents", "incident_id", "id"),
]


def upgrade() -> None:
    for name, table, referent, local, remote in _FKS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, referent, [local], [remote], ondelete="CASCADE")


def downgrade() -> None:
    for name, table, referent, local, remote in _FKS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, referent, [local], [remote])
