"""Merge multiple heads into a single head

Revision ID: merge_heads_20260101
Revises: add_audit_logs_20260101, add_org_scope_001, org_units_001
Create Date: 2026-01-01 03:00:00.000000

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "merge_heads_20260101"
down_revision: Union[str, Sequence[str], None] = (
    "add_audit_logs_20260101",
    "add_org_scope_001",
    "org_units_001",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision: no schema changes.
    pass


def downgrade() -> None:
    # No-op downgrade to avoid schema operations during merges.
    pass
