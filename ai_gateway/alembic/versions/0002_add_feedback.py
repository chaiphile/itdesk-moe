"""add feedback fields to ai_suggestions

Revision ID: 0002_add_feedback
Revises: 0001_create_ai_tables
Create Date: 2026-01-03 00:00:00.000001
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_add_feedback"
down_revision = "0001_create_ai_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ai_suggestions", sa.Column("accepted", sa.Boolean, nullable=True))
    op.add_column("ai_suggestions", sa.Column("rejected", sa.Boolean, nullable=True))
    op.add_column("ai_suggestions", sa.Column("decided_at", sa.DateTime, nullable=True))
    op.add_column("ai_suggestions", sa.Column("feedback_json", sa.JSON, nullable=True))


def downgrade():
    op.drop_column("ai_suggestions", "feedback_json")
    op.drop_column("ai_suggestions", "decided_at")
    op.drop_column("ai_suggestions", "rejected")
    op.drop_column("ai_suggestions", "accepted")
