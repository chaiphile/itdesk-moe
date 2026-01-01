from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import OrgUnit


def _padded(id_: int) -> str:
    return f"{id_:08d}"


def create_org_unit(
    db: Session, name: str, type: str, parent_id: Optional[int] = None
) -> OrgUnit:
    """Create an OrgUnit using two-step insert to compute materialized path.

    - Insert with temporary path and depth=0
    - flush to get id
    - compute path and depth from parent (or root)
    - commit and refresh
    """
    org = OrgUnit(name=name, type=type, parent_id=parent_id, path="", depth=0)
    db.add(org)
    db.flush()  # assigns `org.id`

    padded = _padded(org.id)
    if parent_id:
        parent = db.query(OrgUnit).filter(OrgUnit.id == parent_id).first()
        if parent is None:
            raise ValueError("parent_id does not exist")
        org.path = f"{parent.path}/{padded}"
        org.depth = parent.depth + 1
    else:
        org.path = f"/{padded}"
        org.depth = 1

    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def get_descendants(db: Session, org_unit_id: int) -> List[OrgUnit]:
    """Return all descendant OrgUnit rows (exclude the given node).

    Uses a prefix LIKE query on the materialized `path` column.
    """
    org = db.query(OrgUnit).filter(OrgUnit.id == org_unit_id).first()
    if org is None:
        return []
    prefix = f"{org.path}/%"
    return (
        db.query(OrgUnit).filter(OrgUnit.path.like(prefix)).order_by(OrgUnit.path).all()
    )
