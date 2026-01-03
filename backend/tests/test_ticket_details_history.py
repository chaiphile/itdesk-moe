from app.core.auth import create_access_token
from app.core.org_unit import create_org_unit
from app.models.models import Role, Team, TeamMember, Ticket, TicketMessage, User


def _auth_headers_for_user(username: str):
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_ticket_history_portal_and_agent(client, db):
    # Build simple org tree
    prov = create_org_unit(db, name="P", type="prov")
    reg = create_org_unit(db, name="R", type="reg", parent_id=prov.id)
    school = create_org_unit(db, name="S", type="school", parent_id=reg.id)

    # Create team
    team = Team(name="team_x", org_unit_id=school.id)
    db.add(team)
    db.commit()
    db.refresh(team)

    # Users
    portal_user = User(
        username="portal", email="p@e", role_id=None, org_unit_id=school.id
    )
    agent_a = User(username="agent_a", email="a@e", role_id=None, org_unit_id=school.id)
    # privileged agent role
    priv_role = Role(name="agent_priv", permissions="CONFIDENTIAL_VIEW")
    db.add(priv_role)
    db.commit()
    db.refresh(priv_role)
    agent_priv = User(
        username="agent_priv", email="ap@e", role_id=priv_role.id, org_unit_id=school.id
    )

    db.add_all([portal_user, agent_a, agent_priv])
    db.commit()
    db.refresh(portal_user)
    db.refresh(agent_a)
    db.refresh(agent_priv)

    # Team membership for agents
    tm1 = TeamMember(team_id=team.id, user_id=agent_a.id)
    tm2 = TeamMember(team_id=team.id, user_id=agent_priv.id)
    db.add_all([tm1, tm2])
    db.commit()

    # Tickets: t1 regular, t2 confidential
    t1 = Ticket(
        title="T1",
        description="d",
        created_by=portal_user.id,
        owner_org_unit_id=school.id,
        current_team_id=team.id,
    )
    t2 = Ticket(
        title="T2",
        description="d2",
        created_by=portal_user.id,
        owner_org_unit_id=school.id,
        current_team_id=team.id,
        sensitivity_level="CONFIDENTIAL",
    )
    db.add_all([t1, t2])
    db.commit()
    db.refresh(t1)
    db.refresh(t2)

    # Messages for t1: one PUBLIC, one INTERNAL
    m1 = TicketMessage(
        ticket_id=t1.id, author_id=portal_user.id, type="PUBLIC", body="public1"
    )
    m2 = TicketMessage(
        ticket_id=t1.id, author_id=agent_a.id, type="INTERNAL", body="internal1"
    )
    # Messages for t2
    m3 = TicketMessage(
        ticket_id=t2.id, author_id=agent_priv.id, type="PUBLIC", body="p_conf"
    )
    m4 = TicketMessage(
        ticket_id=t2.id, author_id=agent_priv.id, type="INTERNAL", body="i_conf"
    )
    db.add_all([m1, m2, m3, m4])
    db.commit()

    # Portal user should see only PUBLIC for t1
    headers = _auth_headers_for_user(portal_user.username)
    resp = client.get(f"/tickets/{t1.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "messages" in data
    assert len(data["messages"]) == 1
    assert data["messages"][0]["type"] == "PUBLIC"
    assert data["messages"][0]["body"] == "public1"

    # Agent (team member) should see both messages for t1
    headers = _auth_headers_for_user(agent_a.username)
    resp = client.get(f"/agent/tickets/{t1.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    types = {m["type"] for m in data.get("messages", [])}
    assert "PUBLIC" in types and "INTERNAL" in types

    # Portal GET confidential should return 404
    headers = _auth_headers_for_user(portal_user.username)
    resp = client.get(f"/tickets/{t2.id}", headers=headers)
    assert resp.status_code == 404

    # Agent without CONFIDENTIAL_VIEW should get 404
    headers = _auth_headers_for_user(agent_a.username)
    resp = client.get(f"/agent/tickets/{t2.id}", headers=headers)
    assert resp.status_code == 404

    # Privileged agent should see confidential ticket and messages
    headers = _auth_headers_for_user(agent_priv.username)
    resp = client.get(f"/agent/tickets/{t2.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    types = {m["type"] for m in data.get("messages", [])}
    assert "PUBLIC" in types and "INTERNAL" in types
