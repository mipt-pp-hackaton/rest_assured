"""add is_active / is_superuser / updated_at to users, drop legacy is_admin

Revision ID: 008
Revises: 007
Create Date: 2026-05-21 00:00:01.000000

Rolls the legacy ``users.is_admin`` flag into a richer auth schema:

- ``is_active``     — soft-disable an account without deleting it.
- ``is_superuser``  — replaces ``is_admin``; data is migrated 1:1 so existing
                      admins keep their privileges.
- ``updated_at``    — tz-aware UTC, server-defaulted to now() (project
                      convention — see CLAUDE.md).

This revision is intentionally NOT a merge migration (its parent 007 already
unified the prior heads). That keeps ``alembic downgrade -1`` unambiguous.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, Sequence[str], None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_superuser",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # Preserve admin status for any pre-existing rows before dropping is_admin.
    op.execute("UPDATE users SET is_superuser = is_admin")
    op.drop_column("users", "is_admin")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute("UPDATE users SET is_admin = is_superuser")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "is_superuser")
    op.drop_column("users", "is_active")
