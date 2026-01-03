from app.core.dependencies import require_org_scope
from app.core.org_scope import get_scope_root_path, is_orgunit_in_scope
from app.core.org_unit import create_org_unit
from app.models.models import User


def test_scope_functions_and_dependency(db):
    # Build sample tree: province -> region -> school -> unit
    province = create_org_unit(db, name="Province Z", type="province")
    region = create_org_unit(db, name="Region R", type="region", parent_id=province.id)
    school = create_org_unit(db, name="School S", type="school", parent_id=region.id)
    unit = create_org_unit(db, name="Unit U", type="unit", parent_id=school.id)

    # Create users assigned to the school-level org unit
    # user_self: org_unit at unit level (unit) with SELF scope
    user_self = User(
        username="u_self",
        email="s@e",
        role_id=None,
        org_unit_id=unit.id,
        scope_level="SELF",
    )
    db.add(user_self)
    # user_school: assigned to school with SCHOOL scope
    user_school = User(
        username="u_school",
        email="s2@e",
        role_id=None,
        org_unit_id=school.id,
        scope_level="SCHOOL",
    )
    db.add(user_school)
    # user_region: assigned to region with REGION scope
    user_region = User(
        username="u_region",
        email="r@e",
        role_id=None,
        org_unit_id=region.id,
        scope_level="REGION",
    )
    db.add(user_region)
    # user_province: assigned to province with PROVINCE scope
    user_province = User(
        username="u_prov",
        email="p@e",
        role_id=None,
        org_unit_id=province.id,
        scope_level="PROVINCE",
    )
    db.add(user_province)
    db.commit()

    # SELF: can access only own unit
    assert is_orgunit_in_scope(
        db, user_self.org_unit_id, user_self.scope_level, unit.id
    )
    assert not is_orgunit_in_scope(
        db, user_self.org_unit_id, user_self.scope_level, school.id
    )

    # SCHOOL: can access school and subordinate unit
    assert is_orgunit_in_scope(
        db, user_school.org_unit_id, user_school.scope_level, school.id
    )
    assert is_orgunit_in_scope(
        db, user_school.org_unit_id, user_school.scope_level, unit.id
    )
    assert not is_orgunit_in_scope(
        db, user_school.org_unit_id, user_school.scope_level, region.id
    )

    # REGION: can access school and unit under region
    assert is_orgunit_in_scope(
        db, user_region.org_unit_id, user_region.scope_level, school.id
    )
    assert is_orgunit_in_scope(
        db, user_region.org_unit_id, user_region.scope_level, unit.id
    )
    assert not is_orgunit_in_scope(
        db, user_region.org_unit_id, user_region.scope_level, province.id
    )

    # PROVINCE: can access all under province
    assert is_orgunit_in_scope(
        db, user_province.org_unit_id, user_province.scope_level, region.id
    )
    assert is_orgunit_in_scope(
        db, user_province.org_unit_id, user_province.scope_level, school.id
    )
    assert is_orgunit_in_scope(
        db, user_province.org_unit_id, user_province.scope_level, unit.id
    )

    # Test get_scope_root_path semantics
    school_root = get_scope_root_path(
        db, user_school.org_unit_id, user_school.scope_level
    )
    assert school_root == school.path
    region_root = get_scope_root_path(
        db, user_region.org_unit_id, user_region.scope_level
    )
    assert region_root == region.path

    # Test dependency inner function directly
    dep = require_org_scope(unit.id)
    # user_self should be allowed for own unit
    assert dep(current_user=user_self, db=db) is True
    # user_school should be allowed for unit
    assert dep(current_user=user_school, db=db) is True
    # user_region should be allowed
    assert dep(current_user=user_region, db=db) is True
    # a user assigned to another school should be denied
    other_school = create_org_unit(
        db, name="Other School", type="school", parent_id=region.id
    )
    outsider = User(
        username="outs",
        email="o@e",
        role_id=None,
        org_unit_id=other_school.id,
        scope_level="SELF",
    )
    db.add(outsider)
    db.commit()
    try:
        dep(current_user=outsider, db=db)
        assert False, "Outsider should not be allowed"
    except Exception:
        pass
