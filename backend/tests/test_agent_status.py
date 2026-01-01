from app.core.auth import create_access_token
from app.core.org_unit import create_org_unit
from app.models.models import AuditLog, Role, Team, TeamMember, Ticket, User


def _auth_headers_for_user(username: str):
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_agent_status_scenarios(client, db):
    # Build org trees
    prov1 = create_org_unit(db, name="Prov1", type="province")
    reg1 = create_org_unit(db, name="Reg1", type="region", parent_id=prov1.id)
    sch1 = create_org_unit(db, name="Sch1", type="school", parent_id=reg1.id)

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
    agent_priv = User(
        username="agent_priv",
        email="p@example.com",
        role_id=role_admin.id,
        org_unit_id=reg1.id,
        scope_level="REGION",
    )
    normal_user = User(
        username="normal",
        email="n@example.com",
        role_id=role_normal.id,
        org_unit_id=reg1.id,
        scope_level="REGION",
    )
    db.add_all([agent_a, agent_priv, normal_user])
    db.commit()
    db.refresh(agent_a)
    db.refresh(agent_priv)
    db.refresh(normal_user)

    # Team memberships
    tm1 = TeamMember(team_id=team_x.id, user_id=agent_a.id)
    tm2 = TeamMember(team_id=team_x.id, user_id=agent_priv.id)
    tm3 = TeamMember(team_id=team_y.id, user_id=normal_user.id)
    db.add_all([tm1, tm2, tm3])
    db.commit()

    # Tickets
    # t1 regular in-scope team_x status OPEN
    t1 = Ticket(
        title="T1",
        description="t1",
        created_by=agent_a.id,
        owner_org_unit_id=sch1.id,
        current_team_id=team_x.id,
        sensitivity_level="REGULAR",
        status="OPEN",
    )
    # t2 regular in-scope team_x status RESOLVED
    t2 = Ticket(
        title="T2",
        description="t2",
        created_by=agent_a.id,
        owner_org_unit_id=sch1.id,
        current_team_id=team_x.id,
        sensitivity_level="REGULAR",
        status="RESOLVED",
    )
    # t3 out-of-scope (sch2), team_x
    t3 = Ticket(
        title="T3",
        description="t3",
        created_by=agent_a.id,
        owner_org_unit_id=sch2.id,
        current_team_id=team_x.id,
        sensitivity_level="REGULAR",
        status="OPEN",
    )
    # t4 confidential in-scope team_x status OPEN
    t4 = Ticket(
        title="T4",
        description="t4",
        created_by=agent_a.id,
        owner_org_unit_id=sch1.id,
        current_team_id=team_x.id,
        sensitivity_level="CONFIDENTIAL",
        status="OPEN",
    )
    db.add_all([t1, t2, t3, t4])
    db.commit()
    db.refresh(t1)
    db.refresh(t2)
    db.refresh(t3)
    db.refresh(t4)

    # 1) Valid transition: OPEN -> IN_PROGRESS returns 200 + audit TICKET_STATUS_CHANGED
    headers = _auth_headers_for_user(agent_a.username)
    resp = client.post(
        f"/agent/tickets/{t1.id}/status",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "IN_PROGRESS"
    audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == t1.id,
            AuditLog.action == "TICKET_STATUS_CHANGED",
        )
        .first()
    )
    assert audit is not None
    assert audit.diff_json["status"]["to"] == "IN_PROGRESS"

    # 2) Invalid transition: OPEN -> CLOSED rejected (400)
    # create a fresh open ticket
    t_open = Ticket(
        title="Topen",
        description="topen",
        created_by=agent_a.id,
        owner_org_unit_id=sch1.id,
        current_team_id=team_x.id,
        sensitivity_level="REGULAR",
        status="OPEN",
    )
    db.add(t_open)
    db.commit()
    db.refresh(t_open)
    resp = client.post(
        f"/agent/tickets/{t_open.id}/status", json={"status": "CLOSED"}, headers=headers
    )
    assert resp.status_code == 400

    # 3) RESOLVED -> CLOSED sets closed_at and writes audit with closed_at change
    resp = client.post(
        f"/agent/tickets/{t2.id}/status", json={"status": "CLOSED"}, headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "CLOSED"
    assert data["closed_at"] is not None
    audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == t2.id,
            AuditLog.action == "TICKET_STATUS_CHANGED",
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit is not None
    assert audit.diff_json["closed_at"]["to"] is not None

    # 4) CLOSED -> IN_PROGRESS rejected
    resp = client.post(
        f"/agent/tickets/{t2.id}/status",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    assert resp.status_code == 400

    # 5) Out-of-scope change rejected + PERMISSION_DENIED audit
    resp = client.post(
        f"/agent/tickets/{t3.id}/status",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    assert resp.status_code == 403
    audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ticket_status",
            AuditLog.entity_id == t3.id,
            AuditLog.action == "PERMISSION_DENIED",
        )
        .first()
    )
    assert audit is not None

    # 6) Confidential change without CONFIDENTIAL_VIEW returns 404 and audit PERMISSION_DENIED
    resp = client.post(
        f"/agent/tickets/{t4.id}/status",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    assert resp.status_code == 404
    audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ticket_confidential",
            AuditLog.entity_id == t4.id,
            AuditLog.action == "PERMISSION_DENIED",
        )
        .first()
    )
    assert audit is not None

    # 7) Privileged agent can change status as allowed (confidential ticket)
    headers_priv = _auth_headers_for_user(agent_priv.username)
    resp = client.post(
        f"/agent/tickets/{t4.id}/status",
        json={"status": "IN_PROGRESS"},
        headers=headers_priv,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "IN_PROGRESS"
    audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == t4.id,
            AuditLog.action == "TICKET_STATUS_CHANGED",
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit is not None
    assert audit.diff_json["status"]["to"] == "IN_PROGRESS"
