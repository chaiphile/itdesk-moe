from typing import List
from sqlalchemy.orm import Session

from app.models.models import Ticket, OrgUnit, TeamMember
from app.core.org_scope import get_scope_root_path
from app.core.auth import has_permission


def list_agent_queues(db: Session, current_user) -> List[Ticket]:
    """Return tickets assigned to any team the user is a member of and within org scope.

    Applies CONFIDENTIAL_VIEW filtering and orders by created_at DESC.
    """
    # Determine teams the user belongs to
    user_id = getattr(current_user, "id", None)
    if user_id is None:
        return []

    team_ids = [r[0] for r in db.query(TeamMember.team_id).filter(TeamMember.user_id == user_id).all()]

    # If user is not a team member and not role 'agent' (no direct role check here), return empty list
    if not team_ids:
        # No teams -> no queues to show
        return []

    # Compute scope root path
    viewer_org_unit_id = getattr(current_user, "org_unit_id", None)
    scope_level = getattr(current_user, "scope_level", "SELF")
    if viewer_org_unit_id is None:
        return []

    scope_root = get_scope_root_path(db, viewer_org_unit_id, scope_level)
    if not scope_root:
        return []

    # Query tickets joined to owner OrgUnit for prefix match
    query = (
        db.query(Ticket)
        .join(OrgUnit, Ticket.owner_org_unit_id == OrgUnit.id)
        .filter(OrgUnit.path.startswith(scope_root))
        .filter(Ticket.current_team_id.in_(team_ids))
    )

    # Confidential filtering
    if not has_permission(current_user, "CONFIDENTIAL_VIEW"):
        query = query.filter(Ticket.sensitivity_level != "CONFIDENTIAL")

    return query.order_by(Ticket.created_at.desc()).all()
