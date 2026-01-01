"""Tests for attachments schema and relationships."""
from app.models.models import Attachment


def test_create_attachment_and_relationships(db, sample_user, sample_ticket):
    att = Attachment(
        ticket_id=sample_ticket.id,
        uploaded_by=sample_user.id,
        object_key="object-key-1",
        original_filename="report.pdf",
        mime="application/pdf",
        size=2048,
    )
    db.add(att)
    db.commit()
    db.refresh(att)

    # defaults applied
    assert att.scanned_status == "PENDING"
    assert att.created_at is not None

    # relationship accessible from ticket
    db.refresh(sample_ticket)
    assert len(sample_ticket.attachments) == 1
    loaded = sample_ticket.attachments[0]
    assert loaded.object_key == "object-key-1"
    assert loaded.original_filename == "report.pdf"
    assert loaded.size == 2048
    assert loaded.uploaded_by == sample_user.id
