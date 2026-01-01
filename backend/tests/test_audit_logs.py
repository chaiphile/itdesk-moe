from app.core.auth import create_access_token
from app.models.models import AuditLog, Ticket
from app.core.org_unit import create_org_unit


def test_ticket_create_writes_audit(db, client, sample_user, sample_role):
    token = create_access_token({"sub": sample_user.username})
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"title": "New Issue", "description": "Details", "priority": "low"}

    resp = client.post("/tickets", headers=headers, json=payload)
    assert resp.status_code == 201
    data = resp.json()
    ticket_id = data["id"]

    rows = db.query(AuditLog).filter(AuditLog.action == "TICKET_CREATED").all()
    assert len(rows) == 1
    row = rows[0]
    assert row.entity_type == "ticket"
    assert row.entity_id == ticket_id
    assert isinstance(row.diff_json, dict)
    assert row.diff_json.get("title") == "New Issue"


def test_permission_denied_writes_audit(db, client, sample_role):
    # Build two org units and a user assigned to unit A
    province = create_org_unit(db, name="Prov", type="province")
    region = create_org_unit(db, name="Reg", type="region", parent_id=province.id)
    school_a = create_org_unit(db, name="SchoolA", type="school", parent_id=region.id)
    school_b = create_org_unit(db, name="SchoolB", type="school", parent_id=region.id)

    from app.models.models import User

    user = User(username="u1", email="u1@e", role_id=sample_role.id, org_unit_id=school_a.id, scope_level="SELF")
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create a ticket owned by school_b
    t = Ticket(title="Secret", description="x", status="OPEN", priority="MED", user_id=user.id, owner_org_unit_id=school_b.id)
    db.add(t)
    db.commit()
    db.refresh(t)

    token = create_access_token({"sub": user.username})
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/tickets/{t.id}", headers=headers)
    assert resp.status_code == 403

    rows = db.query(AuditLog).filter(AuditLog.action == "PERMISSION_DENIED").all()
    assert len(rows) >= 1
    # find a row for org_unit_access with matching entity_id
    found = None
    for r in rows:
        if r.entity_type == "org_unit_access" and r.entity_id == school_b.id:
            found = r
            break
    assert found is not None
    assert isinstance(found.meta_json, dict)
    assert "/tickets" in (found.meta_json.get("path") or "")
    assert found.meta_json.get("method") == "GET"
