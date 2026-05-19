"""add owner_emails to services (JSON)

Revision ID: 003
Revises: 002
Create Date: ...
"""

from alembic import op

revision: str = "003"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем JSON‑колонку, если её ещё нет (безопасно для существующих БД)
    op.execute("ALTER TABLE services ADD COLUMN IF NOT EXISTS owner_emails jsonb DEFAULT '[]'")


def downgrade():
    op.drop_column("services", "owner_emails")
