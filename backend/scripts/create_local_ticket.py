from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.models.models import OrgUnit, Ticket, User

settings = get_settings()

Base.metadata.create_all(bind=engine)

session = SessionLocal()
try:
    # find user
    user = session.query(User).filter(User.username == "live_test_user").first()
    if not user:
        raise SystemExit(
            "User live_test_user not found; run create_live_user_and_token first"
        )

    # create org unit
    org = session.query(OrgUnit).filter(OrgUnit.name == "LocalSchool").first()
    if not org:
        org = OrgUnit(
            name="LocalSchool", type="school", parent_id=None, path="/00000001", depth=1
        )
        session.add(org)
        session.commit()
        session.refresh(org)

    user.org_unit_id = org.id
    session.add(user)
    session.commit()
    session.refresh(user)

    # create ticket
    ticket = Ticket(
        title="Live T",
        description="desc",
        status="OPEN",
        priority="MED",
        created_by=user.id,
        owner_org_unit_id=org.id,
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    print("created ticket", ticket.id)
finally:
    session.close()
