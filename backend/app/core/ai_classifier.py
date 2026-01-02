import re
from typing import Any, Dict, Optional, Tuple


def mask_pii(text: str) -> str:
    if not text:
        return text
    # simple regexes for MVP
    # emails
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED]", text)
    # phone numbers (very naive)
    text = re.sub(r"\b\+?\d[\d\-() ]{6,}\d\b", "[REDACTED]", text)
    # national ids (digits, length 6-14)
    text = re.sub(r"\b\d{6,14}\b", "[REDACTED]", text)
    return text


def rules_v1_classify(title: str, description: str, db=None) -> Dict[str, Any]:
    """Baseline rule-based classifier returning the contract schema.

    This is intentionally tiny: it detects a few keywords and maps to
    category/priority. `route_to_team_id` is left None for MVP.
    """
    text = f"{title or ''} {description or ''}".lower()

    category = "GENERAL"
    subcategory = None
    priority = "LOW"
    route_to_team_id = None
    confidence = 0.45
    rationale_short = "rule-based fallback"

    if "password" in text or "login" in text or "credential" in text:
        category = "ACCESS"
        subcategory = "PASSWORD_RESET"
        priority = "HIGH"
        confidence = 0.9
        rationale_short = "detected access/password keywords"
    elif "payment" in text or "invoice" in text or "billing" in text:
        category = "BILLING"
        priority = "MED"
        confidence = 0.8
        rationale_short = "detected billing keywords"
    elif "error" in text or "failed" in text or "exception" in text:
        category = "TECHNICAL"
        priority = "MED"
        confidence = 0.6
        rationale_short = "detected error keywords"

    return {
        "category": category,
        "subcategory": subcategory,
        "priority": priority,
        "route_to_team_id": route_to_team_id,
        "confidence": float(confidence),
        "rationale_short": rationale_short,
    }
