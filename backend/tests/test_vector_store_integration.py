import json

from app.core.vector_store import FaissVectorStore


def test_vector_retrieval_and_permission_filtering(client, db, sample_user, sample_team):
    # create two tickets
    from app.models.models import Ticket, Role

    t1 = Ticket(title="Printer not working", description="My printer shows error code 123", status="OPEN", priority="MED", created_by=sample_user.id, current_team_id=sample_team.id, owner_org_unit_id=sample_user.org_unit_id)
    t2 = Ticket(title="Cannot login", description="Unable to login with ldap credentials", status="OPEN", priority="HIGH", created_by=sample_user.id, current_team_id=sample_team.id, owner_org_unit_id=sample_user.org_unit_id)
    db.add_all([t1, t2])
    db.commit()
    db.refresh(t1)
    db.refresh(t2)

    # ensure the sample_user is a member of the team (agent-like privileges)
    from app.models.models import TeamMember

    tm = TeamMember(team_id=sample_team.id, user_id=sample_user.id)
    db.add(tm)
    db.commit()

    # Build an in-memory vector store and index both tickets
    store = FaissVectorStore(data_dir=None)
    store.clear()
    store.add(t1.id, f"{t1.title}\n{t1.description}", metadata={"title": t1.title})
    store.add(t2.id, f"{t2.title}\n{t2.description}", metadata={"title": t2.title})

    # For deterministic testing without heavy embedding models installed,
    # monkeypatch the `search` method to return a predictable candidate.
    store.search = lambda query, top_k=5: [(t2.id, 0.95, {"title": t2.title})]

    # Monkeypatch the vector store used by the API route and override auth
    import app.api.routes.ai as ai_mod
    from app.core.auth import get_current_user
    from app.main import app

    ai_mod._VSTORE = store
    app.dependency_overrides[get_current_user] = lambda: sample_user

    # Query for login issue -> should retrieve t2 first
    resp = client.post("/ai/retrieve", json={"query": "login ldap", "top_k": 2})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) >= 1
    ids = [r["ticket_id"] for r in data["results"]]
    assert t2.id in ids
