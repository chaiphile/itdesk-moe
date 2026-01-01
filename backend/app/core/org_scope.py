from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import OrgUnit

SCOPE_LEVELS = ("SELF", "SCHOOL", "REGION", "PROVINCE", "MINISTRY")


def _padded(id_: int) -> str:
    return f"{id_:08d}"


def get_ancestor_by_type(
    db: Session, org_unit_id: int, target_type: str
) -> Optional[int]:
    """Return the nearest ancestor id of given type, or None."""
    org = db.query(OrgUnit).filter(OrgUnit.id == org_unit_id).first()
    if org is None:
        return None
    # path format: /00000001/00000002/... -> split into ids
    parts = [p for p in org.path.split("/") if p]
    # walk from nearest ancestor (right-to-left excluding self)
    if not parts:
        return None
    # exclude current node (last) when searching ancestors
    ancestor_ids = [int(p) for p in parts[:-1]]
    # search nearest (last in ancestor_ids)
    for aid in reversed(ancestor_ids):
        row = db.query(OrgUnit).filter(OrgUnit.id == aid).first()
        if row and row.type == target_type:
            return row.id
    return None


def get_scope_root_path(db: Session, viewer_org_unit_id: int, scope_level: str) -> str:
    """Return the materialized path string that defines the root of the scope."""
    viewer = db.query(OrgUnit).filter(OrgUnit.id == viewer_org_unit_id).first()
    if viewer is None:
        return ""

    scope_level = (scope_level or "SELF").upper()
    if scope_level == "SELF":
        return viewer.path

    # Map levels to ancestor types. For SCHOOL, REGION, PROVINCE, MINISTRY
    mapping = {
        "SCHOOL": "school",
        "REGION": "region",
        "PROVINCE": "province",
        "MINISTRY": "ministry",
    }

    target_type = mapping.get(scope_level)
    if not target_type:
        return viewer.path

    # If viewer itself matches, use viewer.path
    if viewer.type == target_type:
        return viewer.path

    ancestor_id = get_ancestor_by_type(db, viewer_org_unit_id, target_type)
    if ancestor_id:
        anc = db.query(OrgUnit).filter(OrgUnit.id == ancestor_id).first()
        if anc:
            return anc.path

    # fallback to viewer.path
    return viewer.path


def is_orgunit_in_scope(
    db: Session, viewer_org_unit_id: int, scope_level: str, target_org_unit_id: int
) -> bool:
    """Return True if target org unit is within the viewer's scope."""
    if viewer_org_unit_id is None or target_org_unit_id is None:
        return False
    scope_root = get_scope_root_path(db, viewer_org_unit_id, scope_level)
    if not scope_root:
        return False

    target = db.query(OrgUnit).filter(OrgUnit.id == target_org_unit_id).first()
    if target is None:
        return False

    # Compare prefix
    return target.path.startswith(scope_root)
