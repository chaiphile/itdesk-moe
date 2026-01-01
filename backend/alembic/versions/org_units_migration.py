"""Add org_units table for materialized-path org tree

Revision ID: org_units_001
Revises: rbac_001
Create Date: 2026-01-01 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'org_units_001'
down_revision: Union[str, Sequence[str], None] = 'rbac_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Create table if not exists (safe for multiple runs)
    op.create_table(
        'org_units',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('depth', sa.Integer(), nullable=False),
    )

    # Create indexes
    op.create_index(op.f('ix_org_units_id'), 'org_units', ['id'], unique=False)
    op.create_index(op.f('ix_org_units_parent_id'), 'org_units', ['parent_id'], unique=False)
    op.create_index(op.f('ix_org_units_path'), 'org_units', ['path'], unique=False)

    # Create foreign key constraint for parent_id -> org_units.id
    try:
        op.create_foreign_key('fk_org_units_parent', 'org_units', 'org_units', ['parent_id'], ['id'])
    except Exception:
        # Some backends (like SQLite) require this to be handled differently. Ignore if it fails.
        pass


def downgrade() -> None:
    # Drop fk if exists
    try:
        op.drop_constraint('fk_org_units_parent', 'org_units', type_='foreignkey')
    except Exception:
        pass

    op.drop_index(op.f('ix_org_units_path'), table_name='org_units')
    op.drop_index(op.f('ix_org_units_parent_id'), table_name='org_units')
    op.drop_index(op.f('ix_org_units_id'), table_name='org_units')
    op.drop_table('org_units')
