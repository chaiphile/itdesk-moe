#!/usr/bin/env python3
"""Seed a small organizational tree: province -> district -> school -> unit"""
from sqlalchemy.orm import sessionmaker
from app.db.session import engine
from app.core.org_unit import create_org_unit

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_org_units():
    db = SessionLocal()
    try:
        # Check if any org_units exist
        from app.models.models import OrgUnit
        if db.query(OrgUnit).count() > 0:
            print("Org units already present; skipping seed.")
            return

        prov = create_org_unit(db, name="Province A", type="province")
        dist = create_org_unit(db, name="District X", type="district", parent_id=prov.id)
        school = create_org_unit(db, name="School 1", type="school", parent_id=dist.id)
        unit = create_org_unit(db, name="Unit 101", type="unit", parent_id=school.id)

        print("Seeded org units:")
        print(prov, dist, school, unit)
    finally:
        db.close()


if __name__ == '__main__':
    seed_org_units()
