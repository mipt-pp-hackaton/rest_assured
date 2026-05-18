"""replace unique constraint on incidents to allow both breach and non-breach open incidents

Revision ID: 004
Revises: 003
Create Date: ...
"""

from alembic import op

revision: str = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    # Удаляем старый уникальный индекс (service_id) WHERE closed_at IS NULL
    op.execute("DROP INDEX IF EXISTS uq_incidents_service_open")
    # Создаём новый составной (service_id, sla_breach) WHERE closed_at IS NULL
    op.execute(
        "CREATE UNIQUE INDEX uq_incidents_service_breach_open "
        "ON incidents (service_id, sla_breach) WHERE closed_at IS NULL"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_incidents_service_breach_open")
    op.execute(
        "CREATE UNIQUE INDEX uq_incidents_service_open "
        "ON incidents (service_id) WHERE closed_at IS NULL"
    )
