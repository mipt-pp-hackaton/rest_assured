"""merge heads 005 and 006

Revision ID: 007
Revises: 005, 006
Create Date: 2026-05-21 00:00:00.000000

Pure merge migration — no schema changes. Unifies the two parallel heads
created by the parallel branches 005 (services.sla_target_pct nullable)
and 006 (users.is_admin), so subsequent revisions have a single linear
predecessor and ``alembic downgrade -1`` is unambiguous.
"""

from typing import Sequence, Union

revision: str = "007"
down_revision: Union[str, Sequence[str], None] = ("005", "006")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
