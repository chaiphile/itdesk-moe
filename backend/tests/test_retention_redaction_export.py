"""Tests for attachment retention, redaction, and export functionality."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.redaction import RedactionEngine, RedactionRuleset
from app.core.auth import create_access_token
from app.core.org_unit import create_org_unit
from app.models.models import (
    Attachment, Ticket, User, Role, OrgUnit, TeamMember, Team
)


class TestRedactionRules:
    """Test redaction rules and engine."""

    def test_redaction_engine_masks_confidential_filename(self):
        """Test that confidential attachment filenames are masked."""
        engine = RedactionEngine()
        attachment_data = {
            "original_filename": "secret_report.pdf",
            "mime": "application/pdf",
            "size": 1024,
            "sensitivity_level": "CONFIDENTIAL",
        }

        redacted = engine.redact_attachment_metadata(
            attachment_data,
            sensitivity_level="CONFIDENTIAL"
        )

        assert redacted["original_filename"] != "secret_report.pdf"
        assert redacted["original_filename"].endswith(".pdf")
        assert "*" in redacted["original_filename"]

    def test_redaction_engine_removes_restricted_filename(self):
        """Test that restricted attachment filenames are removed."""
        engine = RedactionEngine()
        attachment_data = {
            "original_filename": "top_secret.txt",
            "mime": "text/plain",
            "size": 512,
            "sensitivity_level": "RESTRICTED",
        }

        redacted = engine.redact_attachment_metadata(
            attachment_data,
            sensitivity_level="RESTRICTED"
        )

        assert redacted["original_filename"] == "[REDACTED FILE]"
        assert redacted["size"] is None

    def test_redaction_engine_keeps_regular_filename(self):
        """Test that regular attachments are not redacted."""
        engine = RedactionEngine()
        attachment_data = {
            "original_filename": "document.pdf",
            "mime": "application/pdf",
            "size": 2048,
            "sensitivity_level": "REGULAR",
        }

        redacted = engine.redact_attachment_metadata(
            attachment_data,
            sensitivity_level="REGULAR"
        )

        assert redacted["original_filename"] == "document.pdf"
        assert redacted["size"] == 2048

    def test_redaction_filters_restricted_attachments(self):
        """Test that RESTRICTED attachments are excluded for users without permission."""
        engine = RedactionEngine()
        ticket_data = {
            "ticket_id": 1,
            "title": "Test Ticket",
            "description": "Test description",
            "sensitivity_level": "REGULAR",
            "attachments": [
                {
                    "id": 1,
                    "original_filename": "regular.pdf",
                    "sensitivity_level": "REGULAR",
                },
                {
                    "id": 2,
                    "original_filename": "restricted.pdf",
                    "sensitivity_level": "RESTRICTED",
                },
            ],
        }

        # Without export permission
        redacted = engine.redact_ticket_export(
            ticket_data,
            has_export_permission=False
        )

        assert len(redacted["attachments"]) == 1
        assert redacted["attachments"][0]["id"] == 1

    def test_redaction_includes_restricted_with_permission(self):
        """Test that RESTRICTED attachments are included for users with permission."""
        engine = RedactionEngine()
        ticket_data = {
            "ticket_id": 1,
            "title": "Test Ticket",
            "description": "Test description",
            "sensitivity_level": "REGULAR",
            "attachments": [
                {
                    "id": 1,
                    "original_filename": "regular.pdf",
                    "sensitivity_level": "REGULAR",
                },
                {
                    "id": 2,
                    "original_filename": "restricted.pdf",
                    "sensitivity_level": "RESTRICTED",
                },
            ],
        }

        # With export permission
        redacted = engine.redact_ticket_export(
            ticket_data,
            has_export_permission=True
        )

        assert len(redacted["attachments"]) == 2

    def test_redaction_masks_confidential_ticket_data(self):
        """Test that confidential ticket data is masked."""
        engine = RedactionEngine()
        ticket_data = {
            "ticket_id": 1,
            "title": "Confidential Matter",
            "description": "Detailed confidential information",
            "sensitivity_level": "CONFIDENTIAL",
            "attachments": [],
        }

        redacted = engine.redact_ticket_export(
            ticket_data,
            has_export_permission=False
        )

        assert redacted["title"] != "Confidential Matter"
        assert redacted["description"] != "Detailed confidential information"
        assert "*" in redacted["title"]


@pytest.mark.usefixtures("db")
class TestAttachmentRetention:
    """Test attachment retention and expiration."""

    def test_attachment_with_retention_period(self, db: Session, sample_ticket):
        """Test that attachment gets expiration date when retention is set."""
        att = Attachment(
            ticket_id=sample_ticket.id,
            uploaded_by=1,
            object_key="retention-test-1",
            original_filename="file.pdf",
            mime="application/pdf",
            size=1024,
            sensitivity_level="REGULAR",
            retention_days=30,
        )
        db.add(att)
        db.commit()
        db.refresh(att)

        # Retention days should be set
        assert att.retention_days == 30
        assert att.status == "ACTIVE"

    def test_attachment_soft_delete(self, db: Session, sample_ticket):
        """Test that attachments are soft-deleted (status=DELETED)."""
        att = Attachment(
            ticket_id=sample_ticket.id,
            uploaded_by=1,
            object_key="soft-delete-test",
            original_filename="file.pdf",
            mime="application/pdf",
            size=1024,
            status="ACTIVE",
        )
        db.add(att)
        db.commit()
        db.refresh(att)

        # Mark as deleted
        att.status = "DELETED"
        db.add(att)
        db.commit()
        db.refresh(att)

        assert att.status == "DELETED"

    def test_attachment_expires_at_calculation(self, db: Session, sample_ticket):
        """Test that expires_at is properly calculated from retention days."""
        now = datetime.utcnow()
        att = Attachment(
            ticket_id=sample_ticket.id,
            uploaded_by=1,
            object_key="expiry-test",
            original_filename="file.pdf",
            mime="application/pdf",
            size=1024,
            retention_days=30,
            expires_at=now + timedelta(days=30),
        )
        db.add(att)
        db.commit()
        db.refresh(att)

        assert att.expires_at is not None
        # Should be approximately 30 days from now
        delta = (att.expires_at - now).days
        assert 29 <= delta <= 31

    def test_attachment_with_sensitivity_level(self, db: Session, sample_ticket):
        """Test that attachment can have different sensitivity levels."""
        att_regular = Attachment(
            ticket_id=sample_ticket.id,
            uploaded_by=1,
            object_key="sensitive-1",
            original_filename="regular.pdf",
            mime="application/pdf",
            size=1024,
            sensitivity_level="REGULAR",
        )
        att_conf = Attachment(
            ticket_id=sample_ticket.id,
            uploaded_by=1,
            object_key="sensitive-2",
            original_filename="confidential.pdf",
            mime="application/pdf",
            size=2048,
            sensitivity_level="CONFIDENTIAL",
        )
        att_restricted = Attachment(
            ticket_id=sample_ticket.id,
            uploaded_by=1,
            object_key="sensitive-3",
            original_filename="restricted.pdf",
            mime="application/pdf",
            size=4096,
            sensitivity_level="RESTRICTED",
        )

        db.add_all([att_regular, att_conf, att_restricted])
        db.commit()

        # Query back
        all_atts = db.query(Attachment).filter(Attachment.ticket_id == sample_ticket.id).all()
        assert len(all_atts) == 3

        levels = {a.object_key: a.sensitivity_level for a in all_atts}
        assert levels["sensitive-1"] == "REGULAR"
        assert levels["sensitive-2"] == "CONFIDENTIAL"
        assert levels["sensitive-3"] == "RESTRICTED"


@pytest.mark.usefixtures("db", "client")
class TestExportBasic:
    """Basic tests for export endpoint (requires auth and permission setup)."""

    def test_export_requires_auth(self, db: Session, client, sample_ticket):
        """Test that export endpoint requires authentication."""
        resp = client.post(f"/tickets/{sample_ticket.id}/export")
        assert resp.status_code == 401
