from app.core.org_unit import create_org_unit, get_descendants
from app.models.models import OrgUnit


def test_create_org_unit_path_and_depth(db):
    province = create_org_unit(db, name="Province A", type="province")
    district = create_org_unit(
        db, name="District X", type="district", parent_id=province.id
    )
    school = create_org_unit(db, name="School 1", type="school", parent_id=district.id)
    unit = create_org_unit(db, name="Unit 101", type="unit", parent_id=school.id)

    assert province.path == f"/{province.id:08d}"
    assert province.depth == 1

    assert district.path == f"/{province.id:08d}/{district.id:08d}"
    assert district.depth == 2

    assert school.path == f"/{province.id:08d}/{district.id:08d}/{school.id:08d}"
    assert school.depth == 3

    assert unit.path.endswith(f"/{unit.id:08d}")
    assert unit.depth == 4


def test_get_descendants(db):
    province = create_org_unit(db, name="Province B", type="province")
    district = create_org_unit(
        db, name="District Y", type="district", parent_id=province.id
    )
    school = create_org_unit(db, name="School 2", type="school", parent_id=district.id)
    unit = create_org_unit(db, name="Unit 202", type="unit", parent_id=school.id)

    prov_desc = get_descendants(db, province.id)
    # Should include district, school, unit (exclude province itself)
    prov_ids = {o.id for o in prov_desc}
    assert district.id in prov_ids
    assert school.id in prov_ids
    assert unit.id in prov_ids
    assert province.id not in prov_ids

    school_desc = get_descendants(db, school.id)
    school_ids = {o.id for o in school_desc}
    assert unit.id in school_ids
    assert len(school_ids) == 1
