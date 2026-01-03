"""add audit logs table

Revision ID: add_audit_logs_20260101
Revises: add_ticket_core_20260101
Create Date: 2026-01-01 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_audit_logs_20260101"
down_revision = "add_ticket_core_20260101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "audit_logs" not in tables:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("actor_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("entity_type", sa.String(), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("diff_json", pg.JSONB(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("ip", sa.String(), nullable=True),
            sa.Column("user_agent", sa.String(), nullable=True),
            sa.Column("meta_json", pg.JSONB(), nullable=True),
            sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        )
        op.create_index("idx_audit_logs_created_at", "audit_logs", ["created_at"])
        op.create_index("idx_audit_logs_actor_id", "audit_logs", ["actor_id"])
        op.create_index(
            "idx_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"]
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "audit_logs" in tables:
        try:
            op.drop_index("idx_audit_logs_entity", table_name="audit_logs")
        except Exception:
            pass
        try:
            op.drop_index("idx_audit_logs_actor_id", table_name="audit_logs")
        except Exception:
            pass
        try:
            op.drop_index("idx_audit_logs_created_at", table_name="audit_logs")
        except Exception:
            pass
        op.drop_table("audit_logs")
