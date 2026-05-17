"""baseline: users, services, check_results, incidents, notification_log

Revision ID: 0001
Revises:
Create Date: 2026-05-17 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("http_method", sa.String(length=16), nullable=False, server_default="GET"),
        sa.Column("interval_ms", sa.Integer(), nullable=False),
        sa.Column("expected_status", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "check_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
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
        "ix_notification_log_incident_id",
        "notification_log",
        ["incident_id"],
    )
    op.create_index(
        "ix_notification_log_service_id",
        "notification_log",
        ["service_id"],
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
    op.drop_index("ix_check_results_service_checked_desc", table_name="check_results")
    op.drop_index("ix_check_results_service_id", table_name="check_results")
    op.drop_table("check_results")
    op.drop_table("services")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
