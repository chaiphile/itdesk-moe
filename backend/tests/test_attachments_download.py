from app.core.auth import create_access_token
from app.core.org_unit import create_org_unit
from app.core.storage import get_storage_client
from app.models.models import Attachment, AuditLog, Ticket, User, Team, TeamMember, Role


class FakeStorageClient:
    def presign_get(self, *, bucket, key, expires_seconds):
        return "http://example/download"


def _auth_headers_for_user(username: str):
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_portal_download_clean_presigns(db, client, sample_role):
    # create role and user without confidential_view
    role = Role(name="plain", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)

    user = User(username="portal", email="p@example.com", role_id=role.id)
    db.add(user)
    db.commit()
    db.refresh(user)

    school = create_org_unit(db, name="S", type="school")
    user.org_unit_id = school.id
    db.add(user)
    db.commit()

    ticket = Ticket(title="T", description="d", status="OPEN", priority="MED", created_by=user.id, owner_org_unit_id=school.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    att = Attachment(ticket_id=ticket.id, uploaded_by=user.id, object_key="k1", original_filename="f.txt", mime="text/plain", size=10, scanned_status="CLEAN")
    db.add(att)
    db.commit()
    db.refresh(att)

    from app.main import app

    app.dependency_overrides[get_storage_client] = lambda: FakeStorageClient()

    headers = _auth_headers_for_user(user.username)
    resp = client.get(f"/tickets/{ticket.id}/attachments/{att.id}/download", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["download_url"].startswith("http")

    rows = db.query(AuditLog).filter(AuditLog.action == "TICKET_ATTACHMENT_DOWNLOAD_PRESIGNED").all()
    assert len(rows) == 1

    app.dependency_overrides.pop(get_storage_client, None)


def test_portal_download_infected_blocked(db, client):
    role = Role(name="plain2", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)
    user = User(username="portal2", email="p2@example.com", role_id=role.id)
    db.add(user)
    db.commit()
    db.refresh(user)

    school = create_org_unit(db, name="S2", type="school")
    user.org_unit_id = school.id
    db.add(user)
    db.commit()

    ticket = Ticket(title="T2", description="d", status="OPEN", priority="MED", created_by=user.id, owner_org_unit_id=school.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    att = Attachment(ticket_id=ticket.id, uploaded_by=user.id, object_key="k2", original_filename="f2.txt", mime="text/plain", size=10, scanned_status="INFECTED")
    db.add(att)
    db.commit()
    db.refresh(att)

    headers = _auth_headers_for_user(user.username)
    resp = client.get(f"/tickets/{ticket.id}/attachments/{att.id}/download", headers=headers)
    assert resp.status_code == 403

    rows = db.query(AuditLog).filter(AuditLog.action == "ATTACHMENT_DOWNLOAD_BLOCKED").all()
    assert any(r.entity_id == att.id for r in rows)


def test_portal_confidential_without_permission_404(db, client):
    role = Role(name="plain3", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)
    user = User(username="portal3", email="p3@example.com", role_id=role.id)
    db.add(user)
    db.commit()
    db.refresh(user)

    school = create_org_unit(db, name="S3", type="school")
    user.org_unit_id = school.id
    db.add(user)
    db.commit()

    ticket = Ticket(title="TC", description="d", status="OPEN", priority="MED", created_by=user.id, owner_org_unit_id=school.id, sensitivity_level="CONFIDENTIAL")
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    att = Attachment(ticket_id=ticket.id, uploaded_by=user.id, object_key="k3", original_filename="f3.txt", mime="text/plain", size=10, scanned_status="CLEAN")
    db.add(att)
    db.commit()
    db.refresh(att)

    headers = _auth_headers_for_user(user.username)
    resp = client.get(f"/tickets/{ticket.id}/attachments/{att.id}/download", headers=headers)
    assert resp.status_code == 404

    rows = db.query(AuditLog).filter(AuditLog.action == "PERMISSION_DENIED").all()
    assert any(r.entity_type == "ticket_attachment_download" for r in rows)


def test_agent_download_regular_clean(db, client):
    # role for agent
    role = Role(name="agentrole", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)

    team = Team(name="teamx", description="x")
    db.add(team)
    db.commit()
    db.refresh(team)

    agent = User(username="agent1", email="a1@example.com", role_id=role.id)
    db.add(agent)
    db.commit()
    db.refresh(agent)

    tm = TeamMember(team_id=team.id, user_id=agent.id)
    db.add(tm)
    db.commit()

    # Org unit for scope
    school = create_org_unit(db, name="TeamOrg", type="school")
    agent.org_unit_id = school.id
    db.add(agent)
    db.commit()
    db.refresh(agent)

    # ticket assigned to team
    ticket = Ticket(title="TA", description="d", status="OPEN", priority="MED", created_by=agent.id, owner_org_unit_id=school.id, team_id=team.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    att = Attachment(ticket_id=ticket.id, uploaded_by=agent.id, object_key="k4", original_filename="f4.txt", mime="text/plain", size=10, scanned_status="CLEAN")
    db.add(att)
    db.commit()
    db.refresh(att)

    from app.main import app
    app.dependency_overrides[get_storage_client] = lambda: FakeStorageClient()

    headers = _auth_headers_for_user(agent.username)
    resp = client.get(f"/agent/tickets/{ticket.id}/attachments/{att.id}/download", headers=headers)
    assert resp.status_code == 200

    app.dependency_overrides.pop(get_storage_client, None)


def test_agent_confidential_without_permission_404(db, client):
    role = Role(name="agentrole2", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)

    team = Team(name="teamy", description="y")
    db.add(team)
    db.commit()
    db.refresh(team)

    agent = User(username="agent2", email="a2@example.com", role_id=role.id)
    db.add(agent)
    db.commit()
    db.refresh(agent)

    tm = TeamMember(team_id=team.id, user_id=agent.id)
    db.add(tm)
    db.commit()

    ticket = Ticket(title="TC2", description="d", status="OPEN", priority="MED", created_by=agent.id, owner_org_unit_id=None, team_id=team.id, sensitivity_level="CONFIDENTIAL")
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    att = Attachment(ticket_id=ticket.id, uploaded_by=agent.id, object_key="k5", original_filename="f5.txt", mime="text/plain", size=10, scanned_status="CLEAN")
    db.add(att)
    db.commit()
    db.refresh(att)

    headers = _auth_headers_for_user(agent.username)
    resp = client.get(f"/agent/tickets/{ticket.id}/attachments/{att.id}/download", headers=headers)
    assert resp.status_code == 404


def test_idor_attachment_not_belonging_to_ticket_returns_404(db, client):
    role = Role(name="plain6", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)

    user = User(username="u6", email="u6@example.com", role_id=role.id)
    db.add(user)
    db.commit()
    db.refresh(user)

    school = create_org_unit(db, name="S6", type="school")
    user.org_unit_id = school.id
    db.add(user)
    db.commit()

    ticket1 = Ticket(title="T1", description="d", status="OPEN", priority="MED", created_by=user.id, owner_org_unit_id=school.id)
    ticket2 = Ticket(title="T2", description="d", status="OPEN", priority="MED", created_by=user.id, owner_org_unit_id=school.id)
    db.add(ticket1)
    db.add(ticket2)
    db.commit()
    db.refresh(ticket1)
    db.refresh(ticket2)

    att = Attachment(ticket_id=ticket2.id, uploaded_by=user.id, object_key="k6", original_filename="f6.txt", mime="text/plain", size=10, scanned_status="CLEAN")
    db.add(att)
    db.commit()
    db.refresh(att)

    headers = _auth_headers_for_user(user.username)
    # attempt to download attachment att.id via ticket1 -> should 404
    resp = client.get(f"/tickets/{ticket1.id}/attachments/{att.id}/download", headers=headers)
    assert resp.status_code == 404
