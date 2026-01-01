"""Tests for new ticket core schema: tables, models and relationships."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.models import (
    Category,
    OrgUnit,
    Team,
    TeamMember,
    Ticket,
    TicketMessage,
    User,
)


def test_ticket_core_schema_and_relationships(db):
    # create org unit tree
    root = OrgUnit(type="division", name="Root Unit", path="/", depth=0)
    child = OrgUnit(type="team", name="Child Unit", parent=root, path="/1/", depth=1)
    db.add_all([root, child])
    db.commit()
    db.refresh(root)
    db.refresh(child)

    # create user bound to a unit
    user = User(
        username="ticketuser",
        email="ticket@example.com",
        role_id=None,
        org_unit_id=child.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # create team and membership
    team = Team(name="Support Team X", description="Support", org_unit_id=child.id)
    db.add(team)
    db.commit()
    db.refresh(team)

    member = TeamMember(team_id=team.id, user_id=user.id, role_in_team="member")
    db.add(member)
    db.commit()
    db.refresh(member)

    # unique constraint enforcement for team_members
    dup = TeamMember(team_id=team.id, user_id=user.id)
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # create a category
    cat = Category(name="Bug", description="Bug reports")
    db.add(cat)
    db.commit()
    db.refresh(cat)

    # create ticket with defaults (do not pass status/priority/sensitivity)
    ticket = Ticket(
        title="Core ticket",
        description="Core ticket description",
        created_by=user.id,  # legacy column maps to user_id
        owner_org_unit_id=child.id,
        current_team_id=team.id,
        category_id=cat.id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    assert ticket.status == "OPEN"
    assert ticket.priority == "MED"
    assert ticket.sensitivity_level == "REGULAR"

    # add two messages
    m1 = TicketMessage(
        ticket_id=ticket.id, author_id=user.id, type="PUBLIC", body="Public message"
    )
    m2 = TicketMessage(
        ticket_id=ticket.id, author_id=user.id, type="INTERNAL", body="Internal note"
    )
    db.add_all([m1, m2])
    db.commit()

    db.refresh(ticket)
    assert len(ticket.messages) == 2
    # ensure message authors load
    assert ticket.messages[0].author.id == user.id
    assert ticket.messages[1].author.id == user.id
