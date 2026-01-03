from app.core.audit import write_audit
from app.core.auth import get_current_user
from app.core.org_scope import is_orgunit_in_scope
from app.db.session import get_db
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session


def require_org_scope(target_org_unit_id: int):
    """Factory dependency that enforces current user's org scope against a target org unit id."""

    def _dependency(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
        request: Request = None,
    ):
        # current_user is expected to have `org_unit_id` and `scope_level`
        viewer_org_unit_id = getattr(current_user, "org_unit_id", None)
        scope_level = getattr(current_user, "scope_level", "SELF")
        if viewer_org_unit_id is None:
            # record permission denied for missing org unit
            try:
                write_audit(
                    db,
                    actor_id=getattr(current_user, "id", None),
                    action="PERMISSION_DENIED",
                    entity_type="org_unit_access",
                    entity_id=(
                        target_org_unit_id if "target_org_unit_id" in locals() else None
                    ),
                    meta={
                        "path": getattr(request, "url", None)
                        and getattr(request.url, "path", None),
                        "method": getattr(request, "method", None),
                    },
                    ip=(
                        getattr(request, "client", None)
                        and getattr(request.client, "host", None)
                    ),
                    user_agent=(
                        request.headers.get("user-agent")
                        if request is not None
                        else None
                    ),
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no org unit assigned",
            )

        allowed = is_orgunit_in_scope(
            db, viewer_org_unit_id, scope_level, target_org_unit_id
        )
        if not allowed:
            # record permission denied
            try:
                write_audit(
                    db,
                    actor_id=getattr(current_user, "id", None),
                    action="PERMISSION_DENIED",
                    entity_type="org_unit_access",
                    entity_id=target_org_unit_id,
                    meta={
                        "path": getattr(request, "url", None)
                        and getattr(request.url, "path", None),
                        "method": getattr(request, "method", None),
                    },
                    ip=(
                        getattr(request, "client", None)
                        and getattr(request.client, "host", None)
                    ),
                    user_agent=(
                        request.headers.get("user-agent")
                        if request is not None
                        else None
                    ),
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Org unit out of scope"
            )
        return True

    return _dependency
