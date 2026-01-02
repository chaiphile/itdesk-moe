from app.core.auth import create_access_token
from app.core.org_unit import create_org_unit
from app.core.storage import get_storage_client
from app.models.models import Attachment, AuditLog, Ticket, User


class FakeStorageClient:
    def presign_put(self, *, bucket, key, content_type, expires_seconds):
        from app.core.config import get_settings

        settings = get_settings()
        public = settings.S3_PUBLIC_BASE_URL or "http://localhost:9000"
        return f"{public}/upload?X-Amz-Signature=FAKE"


def _auth_headers_for_user(username: str):
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_portal_user_can_presign(db, client, sample_user, sample_role):
    # Create org unit and ticket owned by same org
    school = create_org_unit(db, name="S", type="school")
    sample_user.org_unit_id = school.id
    db.add(sample_user)
    db.commit()
    db.refresh(sample_user)

    ticket = Ticket(title="T", description="d", status="OPEN", priority="MED", created_by=sample_user.id, owner_org_unit_id=school.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Override storage dependency
    from app.main import app

    app.dependency_overrides[get_storage_client] = lambda: FakeStorageClient()

    headers = _auth_headers_for_user(sample_user.username)
    payload = {"original_filename": "report.pdf", "mime": "application/pdf", "size": 1024}
    resp = client.post(f"/tickets/{ticket.id}/attachments/presign", headers=headers, json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "upload_url" in data
    from app.core.config import get_settings
    settings = get_settings()
    public = settings.S3_PUBLIC_BASE_URL or "http://localhost:9000"
    assert data["upload_url"].startswith(public)

    # DB row exists
    att = db.query(Attachment).filter(Attachment.id == data["attachment_id"]).first()
    assert att is not None
    assert att.scanned_status == "PENDING"

    # Audit exists
    a = db.query(AuditLog).filter(AuditLog.action == "TICKET_ATTACHMENT_PRESIGNED").all()
    assert len(a) == 1

    app.dependency_overrides.pop(get_storage_client, None)


def test_size_too_large_rejected(db, client, sample_user, sample_role):
    school = create_org_unit(db, name="S2", type="school")
    sample_user.org_unit_id = school.id
    db.add(sample_user)
    db.commit()
    db.refresh(sample_user)

    ticket = Ticket(title="T2", description="d", status="OPEN", priority="MED", created_by=sample_user.id, owner_org_unit_id=school.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    headers = _auth_headers_for_user(sample_user.username)
    # large size
    payload = {"original_filename": "big.bin", "mime": "application/octet-stream", "size": 9999999999}
    resp = client.post(f"/tickets/{ticket.id}/attachments/presign", headers=headers, json=payload)
    assert resp.status_code == 400


def test_out_of_scope_denied_and_audited(db, client, sample_user, sample_role):
    # Create two orgs, user in A, ticket in B
    a = create_org_unit(db, name="A", type="school")
    b = create_org_unit(db, name="B", type="school")

    sample_user.org_unit_id = a.id
    db.add(sample_user)
    db.commit()
    db.refresh(sample_user)

    ticket = Ticket(title="T3", description="d", status="OPEN", priority="MED", created_by=sample_user.id, owner_org_unit_id=b.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    headers = _auth_headers_for_user(sample_user.username)
    payload = {"original_filename": "x.txt", "mime": "text/plain", "size": 10}
    resp = client.post(f"/tickets/{ticket.id}/attachments/presign", headers=headers, json=payload)
    assert resp.status_code == 403

    rows = db.query(AuditLog).filter(AuditLog.action == "PERMISSION_DENIED").all()
    assert any(r.entity_type == "ticket_attachment" for r in rows)


def test_confidential_without_permission_returns_404_and_audited(db, client, sample_user, sample_role):
    school = create_org_unit(db, name="C", type="school")
    sample_user.org_unit_id = school.id
    db.add(sample_user)
    db.commit()
    db.refresh(sample_user)

    ticket = Ticket(title="TC", description="d", status="OPEN", priority="MED", created_by=sample_user.id, owner_org_unit_id=school.id, sensitivity_level="CONFIDENTIAL")
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    headers = _auth_headers_for_user(sample_user.username)
    payload = {"original_filename": "sec.pdf", "mime": "application/pdf", "size": 100}
    resp = client.post(f"/tickets/{ticket.id}/attachments/presign", headers=headers, json=payload)
    assert resp.status_code == 404

    rows = db.query(AuditLog).filter(AuditLog.action == "PERMISSION_DENIED").all()
    assert any(r.entity_type == "ticket_attachment" for r in rows)
