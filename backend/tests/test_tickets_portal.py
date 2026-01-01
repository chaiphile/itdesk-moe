from app.core.auth import create_access_token
from app.core.org_unit import create_org_unit
from app.models.models import User, Ticket


def _auth_headers_for_user(username: str):
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_cannot_spoof_owner_org_unit_id(client, db):
    # Create two org units and a user assigned to first
    school_a = create_org_unit(db, name="A", type="school")
    school_b = create_org_unit(db, name="B", type="school")

    user = User(username="u1", email="u1@example.com", role_id=None, org_unit_id=school_a.id)
    db.add(user)
    db.commit()
    db.refresh(user)

    headers = _auth_headers_for_user(user.username)
    payload = {"title": "Spoof", "description": "attempt", "owner_org_unit_id": school_b.id}
    resp = client.post("/tickets", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()

    # DB should have owner_org_unit_id == user's org unit, not the spoofed one
    ticket = db.query(Ticket).filter(Ticket.id == data["id"]).first()
    assert ticket is not None
    assert ticket.owner_org_unit_id == school_a.id


def test_scope_list_and_get(client, db):
    # Build tree: province > region > school > unit
    province = create_org_unit(db, name="Prov", type="province")
    region = create_org_unit(db, name="Reg", type="region", parent_id=province.id)
    school = create_org_unit(db, name="Sch", type="school", parent_id=region.id)
    other_school = create_org_unit(db, name="Other", type="school", parent_id=region.id)

    # Create tickets owned by different schools
    author = User(username="author", email="a@e", role_id=None, org_unit_id=school.id)
    db.add(author)
    db.commit()
    db.refresh(author)

    t1 = Ticket(title="T1", description="d", created_by=author.id, owner_org_unit_id=school.id)
    t2 = Ticket(title="T2", description="d", created_by=author.id, owner_org_unit_id=other_school.id)
    db.add_all([t1, t2])
    db.commit()

    # SELF-scoped user at school should see only tickets under their own org
    user_self = User(username="selfuser", email="s@e", role_id=None, org_unit_id=school.id, scope_level="SELF")
    db.add(user_self)
    db.commit()
    db.refresh(user_self)

    headers = _auth_headers_for_user(user_self.username)
    resp = client.get("/tickets/mine", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert any(t["owner_org_unit_id"] == school.id for t in data)
    assert all(t["owner_org_unit_id"] == school.id for t in data)

    # REGION-scoped user at region should see both schools under region
    user_region = User(username="regionuser", email="r@e", role_id=None, org_unit_id=region.id, scope_level="REGION")
    db.add(user_region)
    db.commit()
    db.refresh(user_region)

    headers = _auth_headers_for_user(user_region.username)
    resp = client.get("/tickets/mine", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    owner_ids = {t["owner_org_unit_id"] for t in data}
    assert school.id in owner_ids and other_school.id in owner_ids

    # get by id denies if out of scope for SELF user
    # t2 is in other_school, user_self should be denied
    headers = _auth_headers_for_user(user_self.username)
    resp = client.get(f"/tickets/{t2.id}", headers=headers)
    assert resp.status_code == 403
