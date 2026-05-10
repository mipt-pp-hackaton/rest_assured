"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-07 21:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("http_method", sa.String(), nullable=False, server_default="GET"),
        sa.Column("interval_ms", sa.Integer(), nullable=False),
        sa.Column("expected_status", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "check_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
        sa.Column("is_up", sa.Boolean(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_check_results_service_id", "check_results", ["service_id"])
    op.create_index(
        "ix_check_results_service_checked_desc",
        "check_results",
        ["service_id", sa.text("checked_at DESC")],
    )


def downgrade():
    op.drop_index("ix_check_results_service_checked_desc", table_name="check_results")
    op.drop_index("ix_check_results_service_id", table_name="check_results")
    op.drop_table("check_results")
    op.drop_table("services")
