"""Add hashed_password field to users table

Revision ID: add_password_001
Revises: rbac_001
Create Date: 2026-01-01 01:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_password_001'
down_revision: Union[str, Sequence[str], None] = 'rbac_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add hashed_password column to users table
    op.add_column('users', sa.Column('hashed_password', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove hashed_password column from users table
    op.drop_column('users', 'hashed_password')
