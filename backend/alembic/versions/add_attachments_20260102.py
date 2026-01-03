"""add attachments table

Revision ID: add_attachments_20260102
Revises: merge_heads_20260101
Create Date: 2026-01-02 00:00:00.000000

"""


import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_attachments_20260102"
down_revision = "merge_heads_20260101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "attachments" not in tables:
        op.create_table(
            "attachments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ticket_id", sa.Integer(), nullable=False),
            sa.Column("uploaded_by", sa.Integer(), nullable=True),
            sa.Column("object_key", sa.String(), nullable=False),
            sa.Column("original_filename", sa.String(), nullable=False),
            sa.Column("mime", sa.String(), nullable=True),
            sa.Column("size", sa.BigInteger(), nullable=False),
            sa.Column("checksum", sa.String(), nullable=True),
            sa.Column(
                "scanned_status", sa.String(), nullable=False, server_default="PENDING"
            ),
            sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        )
        op.create_index("idx_attachments_ticket_id", "attachments", ["ticket_id"])
        op.create_index(
            "idx_attachments_scanned_status", "attachments", ["scanned_status"]
        )
        op.create_index(
            "ux_attachments_object_key", "attachments", ["object_key"], unique=True
        )
        op.create_check_constraint(
            "ck_attachments_scanned_status_vals",
            "attachments",
            "scanned_status IN ('PENDING','CLEAN','INFECTED','FAILED')",
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "attachments" in tables:
        try:
            op.drop_index("idx_attachments_ticket_id", table_name="attachments")
        except Exception:
            pass
        try:
            op.drop_index("idx_attachments_scanned_status", table_name="attachments")
        except Exception:
            pass
        try:
            op.drop_index("ux_attachments_object_key", table_name="attachments")
        except Exception:
            pass
        try:
            op.drop_constraint(
                "ck_attachments_scanned_status_vals", "attachments", type_="check"
            )
        except Exception:
            pass
        op.drop_table("attachments")
