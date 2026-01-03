"""Add org_unit_id and scope_level to users table

Revision ID: add_org_scope_001
Revises: add_password_001
Create Date: 2026-01-01 02:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_org_scope_001"
down_revision: Union[str, Sequence[str], None] = "add_password_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add org_unit_id and scope_level."""
    op.add_column("users", sa.Column("org_unit_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_org_unit", "users", "org_units", ["org_unit_id"], ["id"]
    )
    op.add_column(
        "users",
        sa.Column("scope_level", sa.String(), nullable=False, server_default="SELF"),
    )


def downgrade() -> None:
    """Downgrade schema: remove added columns."""
    op.drop_column("users", "scope_level")
    # Drop FK then column
    op.drop_constraint("fk_users_org_unit", "users", type_="foreignkey")
    op.drop_column("users", "org_unit_id")
