"""add retention and redaction fields to attachments

Revision ID: add_retention_redaction_20260102
Revises: add_attachments_20260102
Create Date: 2026-01-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_retention_redaction_20260102'
down_revision = 'add_attachments_20260102'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'attachments' in tables:
        # Add columns if they don't exist
        columns = [col['name'] for col in inspector.get_columns('attachments')]
        
        if 'sensitivity_level' not in columns:
            op.add_column('attachments', sa.Column('sensitivity_level', sa.String(), nullable=False, server_default='REGULAR'))
        
        if 'retention_days' not in columns:
            op.add_column('attachments', sa.Column('retention_days', sa.Integer(), nullable=True))
        
        if 'status' not in columns:
            op.add_column('attachments', sa.Column('status', sa.String(), nullable=False, server_default='ACTIVE'))
        
        if 'redacted_at' not in columns:
            op.add_column('attachments', sa.Column('redacted_at', sa.DateTime(timezone=True), nullable=True))
        
        if 'expires_at' not in columns:
            op.add_column('attachments', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
        
        # Add check constraints
        try:
            op.create_check_constraint(
                'ck_attachments_sensitivity_vals',
                'attachments',
                "sensitivity_level IN ('REGULAR','CONFIDENTIAL','RESTRICTED')"
            )
        except Exception:
            pass
        
        try:
            op.create_check_constraint(
                'ck_attachments_status_vals',
                'attachments',
                "status IN ('ACTIVE','DELETED')"
            )
        except Exception:
            pass
        
        # Add index on expires_at
        try:
            op.create_index('idx_attachments_expires_at', 'attachments', ['expires_at'])
        except Exception:
            pass


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'attachments' in tables:
        columns = [col['name'] for col in inspector.get_columns('attachments')]
        
        try:
            op.drop_index('idx_attachments_expires_at', table_name='attachments')
        except Exception:
            pass
        
        try:
            op.drop_constraint('ck_attachments_sensitivity_vals', 'attachments', type_='check')
        except Exception:
            pass
        
        try:
            op.drop_constraint('ck_attachments_status_vals', 'attachments', type_='check')
        except Exception:
            pass
        
        if 'sensitivity_level' in columns:
            op.drop_column('attachments', 'sensitivity_level')
        
        if 'retention_days' in columns:
            op.drop_column('attachments', 'retention_days')
        
        if 'status' in columns:
            op.drop_column('attachments', 'status')
        
        if 'redacted_at' in columns:
            op.drop_column('attachments', 'redacted_at')
        
        if 'expires_at' in columns:
            op.drop_column('attachments', 'expires_at')
