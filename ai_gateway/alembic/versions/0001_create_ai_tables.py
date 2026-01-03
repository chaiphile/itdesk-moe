"""create ai_suggestions and audit_events

Revision ID: 0001_create_ai_tables
Revises:
Create Date: 2026-01-03 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_create_ai_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_suggestions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ticket_id", sa.String, index=True),
        sa.Column("kind", sa.String, index=True),
        sa.Column("payload_json", sa.JSON),
        sa.Column("model_version", sa.String),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("event_type", sa.String, index=True),
        sa.Column("ticket_id", sa.String, index=True),
        sa.Column("payload_json", sa.JSON),
        sa.Column("created_at", sa.DateTime),
    )


def downgrade():
    op.drop_table("audit_events")
    op.drop_table("ai_suggestions")
