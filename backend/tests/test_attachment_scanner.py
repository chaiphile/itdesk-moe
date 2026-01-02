import io

from unittest.mock import patch

from app.models.models import Attachment, AuditLog


def _make_s3_get_object(body_bytes: bytes):
    class Body:
        def __init__(self, b):
            self._io = io.BytesIO(b)

        def read(self):
            return self._io.read()

    return {"Body": Body(body_bytes)}


def test_scanner_updates_db_and_writes_audit_clean(db):
    # create a PENDING attachment using the test db session
    session = db
    att = Attachment(ticket_id=1, uploaded_by=None, object_key="k-sc-1", original_filename="f.txt", mime="text/plain", size=4, scanned_status="PENDING")
    session.add(att)
    session.commit()
    # reload from DB to get a session-bound instance and id
    att = session.query(Attachment).filter(Attachment.object_key == "k-sc-1").first()

    from scripts.attachment_scanner import scan_pending_once

    # patch boto3 client get_object, clamd scanner and SessionLocal used inside scanner
    with patch("scripts.attachment_scanner.boto3.client") as mock_boto:
        mock_client = mock_boto.return_value
        mock_client.get_object.return_value = _make_s3_get_object(b"data")
        with patch("scripts.attachment_scanner.perform_clamav_instream_scan", return_value="CLEAN"):
            with patch("scripts.attachment_scanner.SessionLocal", new=lambda: session):
                settings = type("S", (), {})()
                # minimal settings required
                settings.S3_ENDPOINT = "http://minio:9000"
                settings.S3_ACCESS_KEY = "minio"
                settings.S3_SECRET_KEY = "change_me"
                settings.S3_REGION = "us-east-1"
                settings.S3_BUCKET = "ticketing-attachments"
                settings.MINIO_BUCKET = None
                settings.CLAMAV_HOST = "clamav"
                settings.CLAMAV_PORT = 3310
                n = scan_pending_once(settings)
                assert n >= 1

    # verify DB updated
    session.expire_all()
    att2 = session.query(Attachment).filter(Attachment.object_key == "k-sc-1").first()
    assert att2 is not None
    assert att2.scanned_status == "CLEAN"

    # audit exists
    rows = session.query(AuditLog).filter(AuditLog.action == "ATTACHMENT_SCANNED").all()
    assert any(r.entity_id == att2.id for r in rows)


def test_scanner_marks_infected(db):
    session = db
    att = Attachment(ticket_id=2, uploaded_by=None, object_key="k-sc-2", original_filename="f2.txt", mime="text/plain", size=6, scanned_status="PENDING")
    session.add(att)
    session.commit()
    att = session.query(Attachment).filter(Attachment.object_key == "k-sc-2").first()

    from scripts.attachment_scanner import scan_pending_once

    with patch("scripts.attachment_scanner.boto3.client") as mock_boto:
        mock_client = mock_boto.return_value
        mock_client.get_object.return_value = _make_s3_get_object(b"eicar")
        with patch("scripts.attachment_scanner.perform_clamav_instream_scan", return_value="INFECTED"):
            with patch("scripts.attachment_scanner.SessionLocal", new=lambda: session):
                settings = type("S", (), {})()
                settings.S3_ENDPOINT = "http://minio:9000"
                settings.S3_ACCESS_KEY = "minio"
                settings.S3_SECRET_KEY = "change_me"
                settings.S3_REGION = "us-east-1"
                settings.S3_BUCKET = "ticketing-attachments"
                settings.MINIO_BUCKET = None
                settings.CLAMAV_HOST = "clamav"
                settings.CLAMAV_PORT = 3310
                n = scan_pending_once(settings)
                assert n >= 1

    session.expire_all()
    att2 = session.query(Attachment).filter(Attachment.object_key == "k-sc-2").first()
    assert att2 is not None
    assert att2.scanned_status == "INFECTED"

    rows = session.query(AuditLog).filter(AuditLog.action == "ATTACHMENT_SCANNED").all()
    assert any(r.entity_id == att2.id for r in rows)
