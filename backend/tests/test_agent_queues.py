from app.core.auth import create_access_token
from app.core.org_unit import create_org_unit
from app.models.models import User, Ticket, Role, Team, TeamMember


def _auth_headers_for_user(username: str):
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_agent_queues_filters(client, db):
    # Build org trees
    prov1 = create_org_unit(db, name="Prov1", type="province")
    reg1 = create_org_unit(db, name="Reg1", type="region", parent_id=prov1.id)
    sch1 = create_org_unit(db, name="Sch1", type="school", parent_id=reg1.id)
    unit1 = create_org_unit(db, name="Unit1", type="unit", parent_id=sch1.id)

    prov2 = create_org_unit(db, name="Prov2", type="province")
    reg2 = create_org_unit(db, name="Reg2", type="region", parent_id=prov2.id)
    sch2 = create_org_unit(db, name="Sch2", type="school", parent_id=reg2.id)

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
    agent_a = User(username="agent_a", email="a@example.com", role_id=role_normal.id, org_unit_id=reg1.id, scope_level="REGION")
    agent_b = User(username="agent_b", email="b@example.com", role_id=role_normal.id, org_unit_id=reg1.id, scope_level="REGION")
    agent_priv = User(username="agent_priv", email="p@example.com", role_id=role_priv.id, org_unit_id=reg1.id, scope_level="REGION")
    db.add_all([agent_a, agent_b, agent_priv])
    db.commit()
    db.refresh(agent_a)
    db.refresh(agent_b)
    db.refresh(agent_priv)

    # Team memberships: agent_a and agent_priv are members of team_x
    tm1 = TeamMember(team_id=team_x.id, user_id=agent_a.id)
    tm2 = TeamMember(team_id=team_x.id, user_id=agent_priv.id)
    db.add_all([tm1, tm2])
    db.commit()

    # Tickets
    # t1: regular, in-scope (sch1), team_x
    t1 = Ticket(title="T1", description="t1", created_by=agent_a.id, owner_org_unit_id=sch1.id, current_team_id=team_x.id, sensitivity_level="REGULAR")
    # t2: regular, OUT of scope (sch2), team_x
    t2 = Ticket(title="T2", description="t2", created_by=agent_a.id, owner_org_unit_id=sch2.id, current_team_id=team_x.id, sensitivity_level="REGULAR")
    # t3: regular, in-scope, team_y
    t3 = Ticket(title="T3", description="t3", created_by=agent_a.id, owner_org_unit_id=sch1.id, current_team_id=team_y.id, sensitivity_level="REGULAR")
    # t4: confidential, in-scope, team_x
    t4 = Ticket(title="T4", description="t4", created_by=agent_a.id, owner_org_unit_id=sch1.id, current_team_id=team_x.id, sensitivity_level="CONFIDENTIAL")
    db.add_all([t1, t2, t3, t4])
    db.commit()
    db.refresh(t1)
    db.refresh(t2)
    db.refresh(t3)
    db.refresh(t4)

    # agent_a should see only t1 (regular, in-scope, team_x)
    headers = _auth_headers_for_user(agent_a.username)
    resp = client.get("/agent/queues", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    ids = {r["id"] for r in data}
    assert t1.id in ids
    assert t2.id not in ids
    assert t3.id not in ids
    assert t4.id not in ids
    # Ensure no description/messages leaked
    for item in data:
        assert "description" not in item

    # agent_priv should see t1 and t4 (has CONFIDENTIAL_VIEW)
    headers = _auth_headers_for_user(agent_priv.username)
    resp = client.get("/agent/queues", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    ids = {r["id"] for r in data}
    assert t1.id in ids and t4.id in ids

    # agent_b has no team membership => 403
    headers = _auth_headers_for_user(agent_b.username)
    resp = client.get("/agent/queues", headers=headers)
    assert resp.status_code == 403
