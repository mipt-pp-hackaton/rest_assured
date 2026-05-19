"""make sla_target_pct nullable

Revision ID: 005
Revises: 004
Create Date: ...
"""

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision = "7e8a423b2aeb"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("services", "sla_target_pct", existing_type=sa.Float(), nullable=True)


def downgrade():
    op.alter_column("services", "sla_target_pct", existing_type=sa.Float(), nullable=False)
