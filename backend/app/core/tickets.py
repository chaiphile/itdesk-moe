from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.models import Ticket
from app.core.org_scope import get_scope_root_path


def create_ticket(db: Session, title: str, description: str, created_by_user, priority: Optional[str] = None) -> Ticket:
    """Create a ticket for the given user. Owner org unit is taken from user profile."""
    priority = (priority or "MED").upper()
    ticket = Ticket(
        title=title,
        description=description,
        priority=priority,
        status="OPEN",
        sensitivity_level="REGULAR",
        created_by=getattr(created_by_user, "id", None),
        owner_org_unit_id=getattr(created_by_user, "org_unit_id", None),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket(db: Session, ticket_id: int) -> Optional[Ticket]:
    return db.query(Ticket).filter(Ticket.id == ticket_id).first()


def list_tickets_in_scope(db: Session, current_user) -> List[Ticket]:
    """Return tickets whose owner_org_unit is within current_user's scope.

    If the user has no org_unit assigned, return empty list.
    """
    viewer_org_unit_id = getattr(current_user, "org_unit_id", None)
    scope_level = getattr(current_user, "scope_level", "SELF")
    if viewer_org_unit_id is None:
        return []

    scope_root = get_scope_root_path(db, viewer_org_unit_id, scope_level)
    if not scope_root:
        return []

    # owner_org_unit.path exists on OrgUnit; use prefix match via join
    from app.models.models import OrgUnit

    return (
        db.query(Ticket)
        .join(OrgUnit, Ticket.owner_org_unit_id == OrgUnit.id)
        .filter(OrgUnit.path.startswith(scope_root))
        .order_by(Ticket.created_at.desc())
        .all()
    )
