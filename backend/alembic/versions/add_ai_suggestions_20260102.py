"""add ai suggestions table

Revision ID: add_ai_suggestions_20260102
Revises: add_audit_logs_20260101
Create Date: 2026-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = 'add_ai_suggestions_20260102'
down_revision = 'add_retention_redaction_20260102'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'ai_suggestions' not in tables:
        op.create_table(
            'ai_suggestions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('ticket_id', sa.Integer(), nullable=False),
            sa.Column('kind', sa.String(), nullable=False),
            sa.Column('payload_json', pg.JSONB(), nullable=False),
            sa.Column('model_version', sa.String(), nullable=False),
            sa.Column('accepted', sa.Boolean(), nullable=True),
            sa.Column('feedback_note', sa.Text(), nullable=True),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('decided_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id']),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.ForeignKeyConstraint(['decided_by'], ['users.id']),
        )
        op.create_index('idx_ai_suggestions_ticket_id', 'ai_suggestions', ['ticket_id'])
        op.create_index('idx_ai_suggestions_kind', 'ai_suggestions', ['kind'])
        op.create_index('idx_ai_suggestions_created_at', 'ai_suggestions', ['created_at'])
        op.create_index('idx_ai_suggestions_accepted', 'ai_suggestions', ['accepted'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'ai_suggestions' in tables:
        try:
            op.drop_index('idx_ai_suggestions_accepted', table_name='ai_suggestions')
        except Exception:
            pass
        try:
            op.drop_index('idx_ai_suggestions_created_at', table_name='ai_suggestions')
        except Exception:
            pass
        try:
            op.drop_index('idx_ai_suggestions_kind', table_name='ai_suggestions')
        except Exception:
            pass
        try:
            op.drop_index('idx_ai_suggestions_ticket_id', table_name='ai_suggestions')
        except Exception:
            pass
        op.drop_table('ai_suggestions')
