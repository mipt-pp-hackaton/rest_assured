"""add incidents and notification_log tables

Revision ID: 002
Revises: 001
Create Date: 2026-05-12 23:57:15.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "service_id",
            sa.Integer(),
            sa.ForeignKey("services.id"),
            nullable=False,
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column(
            "sla_breach",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incidents_service_id", "incidents", ["service_id"])
    op.create_index("ix_incidents_closed_at", "incidents", ["closed_at"])
    op.create_index(
        "uq_incidents_service_open",
        "incidents",
        ["service_id"],
        unique=True,
        postgresql_where=sa.text("closed_at IS NULL"),
    )

    op.create_table(
        "notification_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "incident_id",
            sa.Integer(),
            sa.ForeignKey("incidents.id"),
            nullable=True,
        ),
        sa.Column(
            "service_id",
            sa.Integer(),
            sa.ForeignKey("services.id"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recipients", sa.String(length=500), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_log_incident_id", "notification_log", ["incident_id"],
    )
    op.create_index(
        "ix_notification_log_service_id", "notification_log", ["service_id"],
    )
    op.create_index(
        "ix_notification_log_kind_sent",
        "notification_log",
        ["service_id", "kind", sa.text("sent_at DESC")],
    )


def downgrade():
    op.drop_index("ix_notification_log_kind_sent", table_name="notification_log")
    op.drop_index("ix_notification_log_service_id", table_name="notification_log")
    op.drop_index("ix_notification_log_incident_id", table_name="notification_log")
    op.drop_table("notification_log")
    op.drop_index("uq_incidents_service_open", table_name="incidents")
    op.drop_index("ix_incidents_closed_at", table_name="incidents")
    op.drop_index("ix_incidents_service_id", table_name="incidents")
    op.drop_table("incidents")
