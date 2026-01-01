from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.models import AuditLog


def write_audit(
    db: Session,
    *,
    actor_id: Optional[int],
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    diff: Optional[Dict[str, Any]] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Append-only write of an audit log entry.

    Commits immediately to ensure persistence; this function provides a
    simple, explicit append-only API (no updates/deletes supported).
    """
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        diff_json=diff,
        ip=ip,
        user_agent=user_agent,
        meta_json=meta,
    )
    db.add(entry)
    try:
        db.commit()
        db.refresh(entry)
    except Exception:
        db.rollback()
        raise
    return entry
