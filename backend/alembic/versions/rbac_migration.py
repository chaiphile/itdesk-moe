"""Add RBAC models with Role and updated User

Revision ID: rbac_001
Revises: d11bba1f83d1
Create Date: 2026-01-01 01:13:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "rbac_001"
down_revision: Union[str, Sequence[str], None] = "d11bba1f83d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if roles table exists before creating it
    from sqlalchemy import text

    conn = op.get_bind()

    # For PostgreSQL, check if table exists
    result = conn.execute(
        text(
            """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'roles'
        );
    """
        )
    ).scalar()

    # Only create table if it doesn't exist
    if not result:
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("permissions", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
    op.create_index(op.f("ix_roles_id"), "roles", ["id"], unique=False)
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)

    # Add role_id column to users table
    op.add_column("users", sa.Column("role_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("username", sa.String(), nullable=True))

    # Create foreign key constraint
    op.create_foreign_key(None, "users", "roles", ["role_id"], ["id"])

    # Create index for username
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    # Drop old role column
    op.drop_column("users", "role")

    # Make username not nullable after populating it
    op.alter_column("users", "username", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Add back the role column
    op.add_column(
        "users", sa.Column("role", sa.String(), nullable=False, default="user")
    )

    # Drop the new columns and constraints
    op.drop_constraint(None, "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "username")
    op.drop_column("users", "role_id")

    # Check if roles table exists before dropping it
    from sqlalchemy import text

    conn = op.get_bind()

    # For PostgreSQL, check if table exists
    result = conn.execute(
        text(
            """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'roles'
        );
    """
        )
    ).scalar()

    # Only drop table if it exists
    if result:
        # Drop roles table
        op.drop_index(op.f("ix_roles_name"), table_name="roles")
        op.drop_index(op.f("ix_roles_id"), table_name="roles")
        op.drop_table("roles")
