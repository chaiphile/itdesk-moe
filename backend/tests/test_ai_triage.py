from app.core.auth import create_access_token
from app.models.models import (
    Role,
    Team,
    TeamMember,
    Ticket,
    User,
    AiSuggestion,
    AuditLog,
)
from app.core.org_unit import create_org_unit


def _auth_headers_for_user(username: str):
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_agent_can_create_suggestion(db, client):
    # Setup role, user, team and membership
    role = Role(name="agent", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)

    org = create_org_unit(db, name="Org", type="dept")

    user = User(username="agent1", email="a1@example.com", role_id=role.id, org_unit_id=org.id, scope_level="SELF")
    db.add(user)
    db.commit()
    db.refresh(user)

    team = Team(name="TeamA", description="A")
    db.add(team)
    db.commit()
    db.refresh(team)

    tm = TeamMember(team_id=team.id, user_id=user.id)
    db.add(tm)
    db.commit()

    ticket = Ticket(title="Login issue", description="Cannot login, password reset needed", status="OPEN", priority="LOW", created_by=user.id, current_team_id=team.id, owner_org_unit_id=org.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    headers = _auth_headers_for_user(user.username)
    payload = {"ticket_id": ticket.id, "title": ticket.title, "description": ticket.description}
    resp = client.post("/ai/classify", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "category" in data

    # ai_suggestions row exists
    sug = db.query(AiSuggestion).filter(AiSuggestion.ticket_id == ticket.id).first()
    assert sug is not None
    assert sug.model_version == "rules-v1"

    # audit exists
    audit = db.query(AuditLog).filter(AuditLog.action == "AI_SUGGESTION_CREATED").first()
    assert audit is not None


def test_confidential_ticket_without_permission_denied(db, client):
    # agent role without CONFIDENTIAL_VIEW
    role = Role(name="agent", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)

    org = create_org_unit(db, name="Org2", type="dept")

    user = User(username="agent2", email="a2@example.com", role_id=role.id, org_unit_id=org.id, scope_level="SELF")
    db.add(user)
    db.commit()
    db.refresh(user)

    team = Team(name="TeamB", description="B")
    db.add(team)
    db.commit()
    db.refresh(team)

    tm = TeamMember(team_id=team.id, user_id=user.id)
    db.add(tm)
    db.commit()

    ticket = Ticket(title="Secret", description="This is confidential", status="OPEN", priority="HIGH", created_by=user.id, current_team_id=team.id, owner_org_unit_id=org.id, sensitivity_level="CONFIDENTIAL")
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    headers = _auth_headers_for_user(user.username)
    payload = {"ticket_id": ticket.id, "title": ticket.title, "description": ticket.description}
    resp = client.post("/ai/classify", json=payload, headers=headers)
    assert resp.status_code == 404

    # Ensure PERMISSION_DENIED audit written
    audit = db.query(AuditLog).filter(AuditLog.action == "PERMISSION_DENIED", AuditLog.entity_type == "ai_classify").first()
    assert audit is not None

    # No ai_suggestions created
    sug = db.query(AiSuggestion).filter(AiSuggestion.ticket_id == ticket.id).first()
    assert sug is None


def test_out_of_scope_wrong_team_denied(db, client):
    # agent who is member of TeamX but ticket is in TeamY
    role = Role(name="agent", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)

    org = create_org_unit(db, name="Org3", type="dept")

    user = User(username="agent3", email="a3@example.com", role_id=role.id, org_unit_id=org.id, scope_level="SELF")
    db.add(user)
    db.commit()
    db.refresh(user)

    team_x = Team(name="TeamX", description="X")
    team_y = Team(name="TeamY", description="Y")
    db.add_all([team_x, team_y])
    db.commit()
    db.refresh(team_x)
    db.refresh(team_y)

    tm = TeamMember(team_id=team_x.id, user_id=user.id)
    db.add(tm)
    db.commit()

    ticket = Ticket(title="Other team", description="Wrong team", status="OPEN", priority="LOW", created_by=user.id, current_team_id=team_y.id, owner_org_unit_id=org.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    headers = _auth_headers_for_user(user.username)
    payload = {"ticket_id": ticket.id, "title": ticket.title, "description": ticket.description}
    resp = client.post("/ai/classify", json=payload, headers=headers)
    assert resp.status_code == 403

    audit = db.query(AuditLog).filter(AuditLog.action == "PERMISSION_DENIED", AuditLog.entity_type == "ai_classify").first()
    assert audit is not None


def test_feedback_updates_and_writes_audit(db, client):
    # Setup and create suggestion
    role = Role(name="agent", permissions="read,admin")
    db.add(role)
    db.commit()
    db.refresh(role)

    org = create_org_unit(db, name="OrgF", type="dept")

    user = User(username="agentf", email="af@example.com", role_id=role.id, org_unit_id=org.id, scope_level="SELF")
    db.add(user)
    db.commit()
    db.refresh(user)

    team = Team(name="TeamF", description="F")
    db.add(team)
    db.commit()
    db.refresh(team)

    tm = TeamMember(team_id=team.id, user_id=user.id)
    db.add(tm)
    db.commit()

    ticket = Ticket(title="Feedback", description="Please triage", status="OPEN", priority="LOW", created_by=user.id, current_team_id=team.id, owner_org_unit_id=org.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    headers = _auth_headers_for_user(user.username)
    payload = {"ticket_id": ticket.id, "title": ticket.title, "description": ticket.description}
    resp = client.post("/ai/classify", json=payload, headers=headers)
    assert resp.status_code == 200

    sug = db.query(AiSuggestion).filter(AiSuggestion.ticket_id == ticket.id).first()
    assert sug is not None

    # Send feedback
    fb = {"accepted": True, "feedback_note": "Looks good"}
    resp = client.post(f"/ai/suggestions/{sug.id}/feedback", json=fb, headers=headers)
    assert resp.status_code == 200

    db.refresh(sug)
    assert sug.accepted is True
    assert sug.feedback_note == "Looks good"
    assert sug.decided_by == user.id

    audit = db.query(AuditLog).filter(AuditLog.action == "AI_SUGGESTION_FEEDBACK").first()
    assert audit is not None
