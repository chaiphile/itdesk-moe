from app.core.auth import create_access_token
from app.models.models import (
    Role,
    Team,
    TeamMember,
    Ticket,
    User,
    AiSuggestion,
    KbDocument,
)
from app.core.org_unit import create_org_unit


def _auth_headers_for_user(username: str):
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_agent_can_suggest_reply_with_kb(db, client):
    # Setup role, user, team and membership
    role = Role(name="agent", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)
from app.core.auth import create_access_token
from app.models.models import (
    Role,
    Team,
    TeamMember,
    Ticket,
    User,
    AiSuggestion,
    KbDocument,
)
from app.core.org_unit import create_org_unit


def _auth_headers_for_user(username: str):
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_agent_can_suggest_reply_with_kb(db, client):
    # Setup role, user, team and membership
    role = Role(name="agent", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)
from app.core.auth import create_access_token
from app.models.models import (
    Role,
    Team,
    TeamMember,
    Ticket,
    User,
    AiSuggestion,
    KbDocument,
)
from app.core.org_unit import create_org_unit


def _auth_headers_for_user(username: str):
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_agent_can_suggest_reply_with_kb(db, client):
    role = Role(name="agent", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)

    org = create_org_unit(db, name="KBOrg", type="dept")

    user = User(username="agentkb", email="akb@example.com", role_id=role.id, org_unit_id=org.id, scope_level="SELF")
    db.add(user)
    db.commit()
    db.refresh(user)

    team = Team(name="TeamKB", description="KB team")
    db.add(team)
    db.commit()
    db.refresh(team)

    tm = TeamMember(team_id=team.id, user_id=user.id)
    db.add(tm)
    db.commit()

    doc1 = KbDocument(title="Password Reset", section="Steps", content="To reset your password, go to /reset and follow the steps.")
    doc2 = KbDocument(title="Login Issues", section="Troubleshooting", content="If you cannot login check your username and password. Password reset may help.")
    db.add_all([doc1, doc2])
    db.commit()

    ticket = Ticket(title="Login issue", description="Cannot login, need password reset", status="OPEN", priority="LOW", created_by=user.id, current_team_id=team.id, owner_org_unit_id=org.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    headers = _auth_headers_for_user(user.username)
    payload = {"ticket_id": ticket.id, "description": ticket.description}
    resp = client.post("/ai/suggest-reply", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "draft_reply" in data
    assert isinstance(data.get("citations"), list)
    assert len(data.get("citations")) >= 1

    sug = db.query(AiSuggestion).filter(AiSuggestion.ticket_id == ticket.id, AiSuggestion.kind == "SUGGEST_REPLY").first()
    assert sug is not None
    assert sug.model_version == "RAG-Lite"


def test_agent_suggest_reply_no_kb_warns_and_stores(db, client):
    role = Role(name="agent2", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)

    org = create_org_unit(db, name="KBOrg2", type="dept")

    user = User(username="agentkb2", email="akb2@example.com", role_id=role.id, org_unit_id=org.id, scope_level="SELF")
    db.add(user)
    db.commit()
    db.refresh(user)

    team = Team(name="TeamKB2", description="KB team")
    db.add(team)
    db.commit()
    db.refresh(team)

    tm = TeamMember(team_id=team.id, user_id=user.id)
    db.add(tm)
    db.commit()

    ticket = Ticket(title="Unknown issue", description="Something odd", status="OPEN", priority="LOW", created_by=user.id, current_team_id=team.id, owner_org_unit_id=org.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    headers = _auth_headers_for_user(user.username)
    payload = {"ticket_id": ticket.id, "description": ticket.description}
    resp = client.post("/ai/suggest-reply", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "warnings" in data
    assert data.get("warnings") != []

    sug = db.query(AiSuggestion).filter(AiSuggestion.ticket_id == ticket.id, AiSuggestion.kind == "SUGGEST_REPLY").first()
    assert sug is not None


def test_feedback_updates_suggest_reply_and_writes_audit(db, client):
    role = Role(name="agentf2", permissions="read,admin")
    db.add(role)
    db.commit()
    db.refresh(role)

    org = create_org_unit(db, name="KBOrgF", type="dept")

    user = User(username="agentf2", email="af2@example.com", role_id=role.id, org_unit_id=org.id, scope_level="SELF")
    db.add(user)
    db.commit()
    db.refresh(user)

    team = Team(name="TeamF2", description="F2")
    db.add(team)
    db.commit()
    db.refresh(team)

    tm = TeamMember(team_id=team.id, user_id=user.id)
    db.add(tm)
    db.commit()

    ticket = Ticket(title="Feedback2", description="Please triage", status="OPEN", priority="LOW", created_by=user.id, current_team_id=team.id, owner_org_unit_id=org.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    headers = _auth_headers_for_user(user.username)
    payload = {"ticket_id": ticket.id, "description": ticket.description}
    resp = client.post("/ai/suggest-reply", json=payload, headers=headers)
    assert resp.status_code == 200

    sug = db.query(AiSuggestion).filter(AiSuggestion.ticket_id == ticket.id, AiSuggestion.kind == "SUGGEST_REPLY").first()
    assert sug is not None

    fb = {"accepted": True, "feedback_note": "Looks good"}
    resp = client.post(f"/ai/suggestions/{sug.id}/feedback", json=fb, headers=headers)
    assert resp.status_code == 200

    db.refresh(sug)
    assert sug.accepted is True
    assert sug.feedback_note == "Looks good"
    assert sug.decided_by == user.id



def test_agent_suggest_reply_no_kb_warns_and_stores(db, client):
    role = Role(name="agent2", permissions="read")
    db.add(role)
    db.commit()
    db.refresh(role)

    org = create_org_unit(db, name="KBOrg2", type="dept")

    user = User(username="agentkb2", email="akb2@example.com", role_id=role.id, org_unit_id=org.id, scope_level="SELF")
    db.add(user)
    db.commit()
    db.refresh(user)

    team = Team(name="TeamKB2", description="KB team")
    db.add(team)
    db.commit()
    db.refresh(team)

    tm = TeamMember(team_id=team.id, user_id=user.id)
    db.add(tm)
    db.commit()

    ticket = Ticket(title="Unknown issue", description="Something odd", status="OPEN", priority="LOW", created_by=user.id, current_team_id=team.id, owner_org_unit_id=org.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    headers = _auth_headers_for_user(user.username)
    payload = {"ticket_id": ticket.id, "description": ticket.description}
    resp = client.post("/ai/suggest-reply", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "warnings" in data
    assert data.get("warnings") != []

    sug = db.query(AiSuggestion).filter(AiSuggestion.ticket_id == ticket.id, AiSuggestion.kind == "SUGGEST_REPLY").first()
    assert sug is not None


def test_feedback_updates_suggest_reply_and_writes_audit(db, client):
    # Setup and create suggestion
    role = Role(name="agentf2", permissions="read,admin")
    db.add(role)
    db.commit()
    db.refresh(role)

    org = create_org_unit(db, name="KBOrgF", type="dept")

    user = User(username="agentf2", email="af2@example.com", role_id=role.id, org_unit_id=org.id, scope_level="SELF")
    db.add(user)
    db.commit()
    db.refresh(user)

    team = Team(name="TeamF2", description="F2")
    db.add(team)
    db.commit()
    db.refresh(team)

    tm = TeamMember(team_id=team.id, user_id=user.id)
    db.add(tm)
    db.commit()

    ticket = Ticket(title="Feedback2", description="Please triage", status="OPEN", priority="LOW", created_by=user.id, current_team_id=team.id, owner_org_unit_id=org.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    headers = _auth_headers_for_user(user.username)
    payload = {"ticket_id": ticket.id, "description": ticket.description}
    resp = client.post("/ai/suggest-reply", json=payload, headers=headers)
    assert resp.status_code == 200

    sug = db.query(AiSuggestion).filter(AiSuggestion.ticket_id == ticket.id, AiSuggestion.kind == "SUGGEST_REPLY").first()
    assert sug is not None

    # Send feedback
    fb = {"accepted": True, "feedback_note": "Looks good"}
    resp = client.post(f"/ai/suggestions/{sug.id}/feedback", json=fb, headers=headers)
    assert resp.status_code == 200

    db.refresh(sug)
    assert sug.accepted is True
    assert sug.feedback_note == "Looks good"
    assert sug.decided_by == user.id
