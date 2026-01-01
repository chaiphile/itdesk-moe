from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user
from app.core.org_scope import is_orgunit_in_scope


def require_org_scope(target_org_unit_id: int):
    """Factory dependency that enforces current user's org scope against a target org unit id."""
    def _dependency(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
        # current_user is expected to have `org_unit_id` and `scope_level`
        viewer_org_unit_id = getattr(current_user, "org_unit_id", None)
        scope_level = getattr(current_user, "scope_level", "SELF")
        if viewer_org_unit_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no org unit assigned")

        allowed = is_orgunit_in_scope(db, viewer_org_unit_id, scope_level, target_org_unit_id)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Org unit out of scope")
        return True

    return _dependency
