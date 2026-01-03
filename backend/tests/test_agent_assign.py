from app.core.auth import create_access_token
from app.core.org_unit import create_org_unit
from app.models.models import AuditLog, Role, Team, TeamMember, Ticket, User


def _auth_headers_for_user(username: str):
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_agent_assign_scenarios(client, db):
    # Build org trees
    prov1 = create_org_unit(db, name="Prov1", type="province")
    reg1 = create_org_unit(db, name="Reg1", type="region", parent_id=prov1.id)
    sch1 = create_org_unit(db, name="Sch1", type="school", parent_id=reg1.id)
    _unit1 = create_org_unit(db, name="Unit1", type="unit", parent_id=sch1.id)

    prov2 = create_org_unit(db, name="Prov2", type="province")
    reg2 = create_org_unit(db, name="Reg2", type="region", parent_id=prov2.id)
    sch2 = create_org_unit(db, name="Sch2", type="school", parent_id=reg2.id)

    # Roles
    role_normal = Role(name="normal", permissions="read")
    role_conf = Role(name="conf", permissions="read,CONFIDENTIAL_VIEW")
    role_admin = Role(name="adminrole", permissions="read,admin,CONFIDENTIAL_VIEW")
    db.add_all([role_normal, role_conf, role_admin])
    db.commit()
    db.refresh(role_normal)
    db.refresh(role_conf)
    db.refresh(role_admin)

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
        org_unit_id=reg1.id,
        scope_level="REGION",
    )
    agent_b = User(
        username="agent_b",
        email="b@example.com",
        role_id=role_normal.id,
        org_unit_id=reg1.id,
        scope_level="REGION",
    )
    agent_c = User(
        username="agent_c",
        email="c@example.com",
        role_id=role_normal.id,
        org_unit_id=reg1.id,
        scope_level="REGION",
    )
    agent_admin = User(
        username="agent_admin",
        email="adm@example.com",
        role_id=role_admin.id,
        org_unit_id=reg1.id,
        scope_level="REGION",
    )
    agent_conf = User(
        username="agent_conf",
        email="p@example.com",
        role_id=role_conf.id,
        org_unit_id=reg1.id,
        scope_level="REGION",
    )
    db.add_all([agent_a, agent_b, agent_c, agent_admin, agent_conf])
    db.commit()
    db.refresh(agent_a)
    db.refresh(agent_b)
    db.refresh(agent_c)
    db.refresh(agent_admin)
    db.refresh(agent_conf)

    # Team memberships: agent_a, agent_b, agent_admin, agent_conf are members of team_x; agent_c in team_y
    tm1 = TeamMember(team_id=team_x.id, user_id=agent_a.id)
    tm2 = TeamMember(team_id=team_x.id, user_id=agent_b.id)
    tm3 = TeamMember(team_id=team_x.id, user_id=agent_admin.id)
    tm4 = TeamMember(team_id=team_x.id, user_id=agent_conf.id)
    tm5 = TeamMember(team_id=team_y.id, user_id=agent_c.id)
    db.add_all([tm1, tm2, tm3, tm4, tm5])
    db.commit()

    # Tickets
    # t1: regular, in-scope team_x
    t1 = Ticket(
        title="T1",
        description="t1",
        created_by=agent_a.id,
        owner_org_unit_id=sch1.id,
        current_team_id=team_x.id,
        sensitivity_level="REGULAR",
    )
    # t2: confidential, in-scope team_x
    t2 = Ticket(
        title="T2",
        description="t2",
        created_by=agent_a.id,
        owner_org_unit_id=sch1.id,
        current_team_id=team_x.id,
        sensitivity_level="CONFIDENTIAL",
    )
    # t3: out-of-scope (sch2), team_x
    t3 = Ticket(
        title="T3",
        description="t3",
        created_by=agent_a.id,
        owner_org_unit_id=sch2.id,
        current_team_id=team_x.id,
        sensitivity_level="REGULAR",
    )
    db.add_all([t1, t2, t3])
    db.commit()
    db.refresh(t1)
    db.refresh(t2)
    db.refresh(t3)

    # 1) agent_a self-assign t1 => 200, audit TICKET_ASSIGNED
    headers = _auth_headers_for_user(agent_a.username)
    resp = client.post(f"/agent/tickets/{t1.id}/assign", json={}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["assignee_id"] == agent_a.id
    # audit record
    audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == t1.id,
            AuditLog.action == "TICKET_ASSIGNED",
        )
        .first()
    )
    assert audit is not None
    assert audit.diff_json["assignee_id"]["to"] == agent_a.id

    # 2) agent_a assign t1 to agent_b => non-admin should get 403
    resp = client.post(
        f"/agent/tickets/{t1.id}/assign",
        json={"assignee_id": agent_b.id},
        headers=headers,
    )
    assert resp.status_code == 403

    # 3) agent_a assign t1 to agent_c (different team) => 400
    resp = client.post(
        f"/agent/tickets/{t1.id}/assign",
        json={"assignee_id": agent_c.id},
        headers=headers,
    )
    assert resp.status_code == 400

    # 4) agent_a cannot assign out-of-scope t3 => 403 + PERMISSION_DENIED audit
    resp = client.post(f"/agent/tickets/{t3.id}/assign", json={}, headers=headers)
    assert resp.status_code == 403
    audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ticket_assign",
            AuditLog.entity_id == t3.id,
            AuditLog.action == "PERMISSION_DENIED",
        )
        .first()
    )
    assert audit is not None

    # 5) agent_a cannot assign confidential t2 without CONFIDENTIAL_VIEW => 404 and audit ticket_confidential
    resp = client.post(f"/agent/tickets/{t2.id}/assign", json={}, headers=headers)
    assert resp.status_code == 404
    audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ticket_confidential",
            AuditLog.entity_id == t2.id,
            AuditLog.action == "PERMISSION_DENIED",
        )
        .first()
    )
    assert audit is not None

    # 6) privileged/admin agent can assign within team to others
    headers_admin = _auth_headers_for_user(agent_admin.username)
    resp = client.post(
        f"/agent/tickets/{t1.id}/assign",
        json={"assignee_id": agent_b.id},
        headers=headers_admin,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assignee_id"] == agent_b.id
    audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == t1.id,
            AuditLog.action == "TICKET_ASSIGNED",
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit is not None
    assert audit.diff_json["assignee_id"]["to"] == agent_b.id
