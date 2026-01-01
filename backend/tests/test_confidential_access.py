from app.core.auth import create_access_token
from app.core.org_unit import create_org_unit
from app.models.models import User, Ticket, Role, AuditLog


def _auth_headers_for_user(username: str):
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_confidential_portal_access(client, db):
    # Build org tree
    province = create_org_unit(db, name="Prov", type="province")
    region = create_org_unit(db, name="Reg", type="region", parent_id=province.id)
    school = create_org_unit(db, name="Sch", type="school", parent_id=region.id)

    # Create roles: one without confidential permission, one with
    role_normal = Role(name="normal", permissions="read")
    role_priv = Role(name="privileged", permissions="read,CONFIDENTIAL_VIEW")
    db.add_all([role_normal, role_priv])
    db.commit()
    db.refresh(role_normal)
    db.refresh(role_priv)

    # Users
    user_normal = User(username="normal_user", email="n@example.com", role_id=role_normal.id, org_unit_id=school.id)
    user_priv = User(username="priv_user", email="p@example.com", role_id=role_priv.id, org_unit_id=school.id)
    db.add_all([user_normal, user_priv])
    db.commit()
    db.refresh(user_normal)
    db.refresh(user_priv)

    # Create tickets in same org: one regular, one confidential
    t_regular = Ticket(title="R", description="reg", created_by=user_priv.id, owner_org_unit_id=school.id, sensitivity_level="REGULAR")
    t_conf = Ticket(title="C", description="conf", created_by=user_priv.id, owner_org_unit_id=school.id, sensitivity_level="CONFIDENTIAL")
    db.add_all([t_regular, t_conf])
    db.commit()
    db.refresh(t_regular)
    db.refresh(t_conf)

    # user_normal: should only see regular in /tickets/mine
    headers = _auth_headers_for_user(user_normal.username)
    resp = client.get("/tickets/mine", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    ids = {t["id"] for t in data}
    assert t_regular.id in ids
    assert t_conf.id not in ids

    # user_normal: GET confidential by id => 404 and audit logged
    resp = client.get(f"/tickets/{t_conf.id}", headers=headers)
    assert resp.status_code == 404

    # Ensure audit row exists for denial
    audit = db.query(AuditLog).filter(AuditLog.entity_type == "ticket_confidential", AuditLog.entity_id == t_conf.id, AuditLog.action == "PERMISSION_DENIED").first()
    assert audit is not None

    # user_priv: should see both in /tickets/mine and GET by id returns 200
    headers = _auth_headers_for_user(user_priv.username)
    resp = client.get("/tickets/mine", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    ids = {t["id"] for t in data}
    assert t_regular.id in ids and t_conf.id in ids

    resp = client.get(f"/tickets/{t_conf.id}", headers=headers)
    assert resp.status_code == 200
