from app.core.auth import create_access_token
from app.core.org_unit import create_org_unit
from app.models.models import (
    AuditLog,
    Role,
    Team,
    TeamMember,
    Ticket,
    TicketMessage,
    User,
)


def _auth_headers_for_user(username: str):
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_agent_message_posting_and_access(client, db):
    # Org tree
    prov = create_org_unit(db, name="Prov", type="province")
    reg = create_org_unit(db, name="Reg", type="region", parent_id=prov.id)
    sch = create_org_unit(db, name="Sch", type="school", parent_id=reg.id)

    # Roles
    role_normal = Role(name="normal", permissions="read")
    role_priv = Role(name="privileged", permissions="read,CONFIDENTIAL_VIEW")
    db.add_all([role_normal, role_priv])
    db.commit()
    db.refresh(role_normal)
    db.refresh(role_priv)

    # Teams
    team_x = Team(name="Team X")
    team_y = Team(name="Team Y")
    db.add_all([team_x, team_y])
    db.commit()
    db.refresh(team_x)
    db.refresh(team_y)

    # Users
    agent_a = User(
        username="agent_a",
        email="a@example.com",
        role_id=role_normal.id,
        org_unit_id=reg.id,
        scope_level="REGION",
    )
    agent_priv = User(
        username="agent_priv",
        email="p@example.com",
        role_id=role_priv.id,
        org_unit_id=reg.id,
        scope_level="REGION",
    )
    normal_user = User(
        username="normal_user",
        email="n@example.com",
        role_id=role_normal.id,
        org_unit_id=sch.id,
    )
    db.add_all([agent_a, agent_priv, normal_user])
    db.commit()
    db.refresh(agent_a)
    db.refresh(agent_priv)
    db.refresh(normal_user)

    # Team memberships: agent_a and agent_priv -> team_x
    tm1 = TeamMember(team_id=team_x.id, user_id=agent_a.id)
    tm2 = TeamMember(team_id=team_x.id, user_id=agent_priv.id)
    db.add_all([tm1, tm2])
    db.commit()

    # Tickets
    t1 = Ticket(
        title="T1",
        description="t1",
        created_by=agent_a.id,
        owner_org_unit_id=sch.id,
        current_team_id=team_x.id,
        sensitivity_level="REGULAR",
    )
    t2 = Ticket(
        title="T2",
        description="t2",
        created_by=agent_a.id,
        owner_org_unit_id=sch.id,
        current_team_id=team_x.id,
        sensitivity_level="CONFIDENTIAL",
    )
    t_out = Ticket(
        title="T3",
        description="t3",
        created_by=agent_a.id,
        owner_org_unit_id=prov.id,  # out of agent_a REGION scope (sch->reg allowed, prov is above)
        current_team_id=team_y.id,
        sensitivity_level="REGULAR",
    )
    db.add_all([t1, t2, t_out])
    db.commit()
    db.refresh(t1)
    db.refresh(t2)
    db.refresh(t_out)

    # 1) agent_a posts INTERNAL to t1 => 200 and audit exists
    headers = _auth_headers_for_user(agent_a.username)
    resp = client.post(f"/agent/tickets/{t1.id}/messages", json={"type": "INTERNAL", "body": " internal note "}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticket_id"] == t1.id
    msg = db.query(TicketMessage).filter(TicketMessage.id == data["id"]).first()
    assert msg is not None and msg.body == "internal note"
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.action == "TICKET_MESSAGE_CREATED", AuditLog.entity_type == "ticket_message", AuditLog.entity_id == msg.id)
        .first()
    )
    assert audit is not None

    # 2) agent_a posts PUBLIC to t1 => 200
    resp = client.post(f"/agent/tickets/{t1.id}/messages", json={"type": "PUBLIC", "body": "public note"}, headers=headers)
    assert resp.status_code == 200

    # 3) normal_user (non-agent) calling agent endpoint => 403
    headers = _auth_headers_for_user(normal_user.username)
    resp = client.post(f"/agent/tickets/{t1.id}/messages", json={"type": "PUBLIC", "body": "x"}, headers=headers)
    assert resp.status_code == 403

    # 4) agent_a posts to confidential t2 without CONFIDENTIAL_VIEW => 404 + PERMISSION_DENIED audit
    headers = _auth_headers_for_user(agent_a.username)
    resp = client.post(f"/agent/tickets/{t2.id}/messages", json={"type": "PUBLIC", "body": "x"}, headers=headers)
    assert resp.status_code == 404
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "ticket_message", AuditLog.entity_id == t2.id, AuditLog.action == "PERMISSION_DENIED")
        .first()
    )
    assert audit is not None

    # 5) out-of-scope or wrong-team ticket => 403 + PERMISSION_DENIED audit
    headers = _auth_headers_for_user(agent_a.username)
    resp = client.post(f"/agent/tickets/{t_out.id}/messages", json={"type": "PUBLIC", "body": "x"}, headers=headers)
    assert resp.status_code == 403
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "ticket_message", AuditLog.entity_id == t_out.id, AuditLog.action == "PERMISSION_DENIED")
        .first()
    )
    assert audit is not None
