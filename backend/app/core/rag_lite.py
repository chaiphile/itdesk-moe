from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.models import KbDocument


def retrieve_kb(db: Session, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Simple retrieval: find KB documents matching query using ILIKE.

    Returns list of dicts with id, title, section, content, score.
    """
    if not query:
        return []

    # Build simple OR conditions for any significant token in the query
    words = [w.strip() for w in query.split() if len(w.strip()) >= 3]
    if not words:
        words = [query]
    conds = []
    for w in words:
        q = f"%{w}%"
        conds.append(KbDocument.title.ilike(q))
        conds.append(KbDocument.content.ilike(q))

    docs = db.query(KbDocument).filter(or_(*conds)).all() if conds else []

    results = []
    for d in docs:
        title_match = query.lower() in (d.title or "").lower()
        content_match = query.lower() in (d.content or "").lower()
        score = 0
        if title_match:
            score += 2
        if content_match:
            score += 1
        # prefer shorter content for snippet
        score += max(0, 1 - (len((d.content or "")) // 2000))
        results.append({"id": d.id, "title": d.title, "section": d.section, "content": d.content, "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def generate_suggestion_from_docs(ticket_title: str, ticket_description: str, docs: List[Dict[str, Any]], language: str = "en") -> Dict[str, Any]:
    """Generate a simple draft reply and citations based only on retrieved docs.

    This is RAG-Lite: no LLM calls, just synthesize a short reply referencing docs.
    """
    citations = []
    for d in docs:
        citations.append({"doc_id": d["id"], "title": d.get("title"), "section": d.get("section")})

    if docs:
        intro = "I found relevant documentation that may help:"
        lines = [f"- {c['title']}{(' — ' + c['section']) if c.get('section') else ''}" for c in citations]
        draft = (
            f"Hi,\n\nThanks for the report about '{ticket_title}'. {intro}\n" + "\n".join(lines) +
            "\n\nPlease follow the referenced guidance and let us know if that resolves the issue."
        )
        warnings = []
    else:
        draft = (
            f"Hi,\n\nThanks for the report about '{ticket_title}'. I couldn't find a matching knowledge base article. "
            "Please provide more details and we'll investigate further."
        )
        warnings = ["No KB matches found"]

    return {"draft_reply": draft, "citations": citations, "warnings": warnings}
