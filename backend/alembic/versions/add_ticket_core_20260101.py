"""add ticket core schema

Revision ID: add_ticket_core_20260101
Revises: d11bba1f83d1
Create Date: 2026-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_ticket_core_20260101'
down_revision = 'd11bba1f83d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # teams: add org_unit_id if missing
    if 'teams' in tables:
        cols = [c['name'] for c in inspector.get_columns('teams')]
        if 'org_unit_id' not in cols:
            op.add_column('teams', sa.Column('org_unit_id', sa.Integer(), nullable=True))
            op.create_foreign_key('fk_teams_org_unit_id', 'teams', 'org_units', ['org_unit_id'], ['id'])
            op.create_index(op.f('ix_teams_org_unit_id'), 'teams', ['org_unit_id'], unique=False)

    # create categories table if not exists
    if 'categories' not in tables:
        op.create_table(
            'categories',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.UniqueConstraint('name'),
        )
        op.create_index(op.f('ix_categories_name'), 'categories', ['name'], unique=True)

    # team_members table
    if 'team_members' not in tables:
        op.create_table(
            'team_members',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('team_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('role_in_team', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_team_members_id'), 'team_members', ['id'], unique=False)
        op.create_index(op.f('ux_team_members_team_user'), 'team_members', ['team_id', 'user_id'], unique=True)

    # tickets: add new columns if missing
    if 'tickets' in tables:
        cols = [c['name'] for c in inspector.get_columns('tickets')]
        if 'owner_org_unit_id' not in cols:
            op.add_column('tickets', sa.Column('owner_org_unit_id', sa.Integer(), nullable=False))
            op.create_foreign_key('fk_tickets_owner_org_unit_id', 'tickets', 'org_units', ['owner_org_unit_id'], ['id'])
            op.create_index('idx_tickets_owner_org_unit_id', 'tickets', ['owner_org_unit_id'])
        if 'assignee_id' not in cols:
            op.add_column('tickets', sa.Column('assignee_id', sa.Integer(), nullable=True))
            op.create_foreign_key('fk_tickets_assignee_id', 'tickets', 'users', ['assignee_id'], ['id'])
        if 'category_id' not in cols:
            op.add_column('tickets', sa.Column('category_id', sa.Integer(), nullable=True))
            op.create_foreign_key('fk_tickets_category_id', 'tickets', 'categories', ['category_id'], ['id'])
        if 'sensitivity_level' not in cols:
            op.add_column('tickets', sa.Column('sensitivity_level', sa.String(), nullable=False, server_default='REGULAR'))
            op.create_check_constraint('ck_tickets_sensitivity_vals', 'tickets', "sensitivity_level IN ('REGULAR','CONFIDENTIAL')")
        if 'closed_at' not in cols:
            op.add_column('tickets', sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))
        # add indexes
        if 'status' in cols:
            op.create_index('idx_tickets_status', 'tickets', ['status'])
        if 'team_id' in cols:
            op.create_index('idx_tickets_current_team_id', 'tickets', ['team_id'])
        if 'created_at' in cols:
            op.create_index('idx_tickets_created_at', 'tickets', ['created_at'])

    # ticket_messages table
    if 'ticket_messages' not in tables:
        op.create_table(
            'ticket_messages',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('ticket_id', sa.Integer(), nullable=False),
            sa.Column('author_id', sa.Integer(), nullable=False),
            sa.Column('type', sa.String(), nullable=False, server_default='PUBLIC'),
            sa.Column('body', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id']),
            sa.ForeignKeyConstraint(['author_id'], ['users.id']),
        )
        op.create_index('idx_ticket_messages_ticket_id_created_at', 'ticket_messages', ['ticket_id', 'created_at'])
        op.create_check_constraint('ck_ticket_messages_type_vals', 'ticket_messages', "type IN ('PUBLIC','INTERNAL')")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'ticket_messages' in tables:
        op.drop_index('idx_ticket_messages_ticket_id_created_at', table_name='ticket_messages')
        op.drop_table('ticket_messages')

    # remove added ticket columns if exist
    if 'tickets' in tables:
        cols = [c['name'] for c in inspector.get_columns('tickets')]
        if 'closed_at' in cols:
            op.drop_column('tickets', 'closed_at')
        if 'sensitivity_level' in cols:
            op.drop_constraint('ck_tickets_sensitivity_vals', 'tickets', type_='check')
            op.drop_column('tickets', 'sensitivity_level')
        if 'category_id' in cols:
            op.drop_constraint('fk_tickets_category_id', 'tickets', type_='foreignkey')
            op.drop_column('tickets', 'category_id')
        if 'assignee_id' in cols:
            op.drop_constraint('fk_tickets_assignee_id', 'tickets', type_='foreignkey')
            op.drop_column('tickets', 'assignee_id')
        if 'owner_org_unit_id' in cols:
            try:
                op.drop_index('idx_tickets_owner_org_unit_id', table_name='tickets')
            except Exception:
                pass
            op.drop_constraint('fk_tickets_owner_org_unit_id', 'tickets', type_='foreignkey')
            op.drop_column('tickets', 'owner_org_unit_id')
        try:
            op.drop_index('idx_tickets_status', table_name='tickets')
        except Exception:
            pass
        try:
            op.drop_index('idx_tickets_current_team_id', table_name='tickets')
        except Exception:
            pass
        try:
            op.drop_index('idx_tickets_created_at', table_name='tickets')
        except Exception:
            pass

    if 'team_members' in tables:
        try:
            op.drop_index(op.f('ux_team_members_team_user'), table_name='team_members')
        except Exception:
            pass
        op.drop_table('team_members')

    if 'categories' in tables:
        try:
            op.drop_index(op.f('ix_categories_name'), table_name='categories')
        except Exception:
            pass
        op.drop_table('categories')

    if 'teams' in tables:
        cols = [c['name'] for c in inspector.get_columns('teams')]
        if 'org_unit_id' in cols:
            try:
                op.drop_index(op.f('ix_teams_org_unit_id'), table_name='teams')
            except Exception:
                pass
            op.drop_constraint('fk_teams_org_unit_id', 'teams', type_='foreignkey')
            op.drop_column('teams', 'org_unit_id')
*** End Patch