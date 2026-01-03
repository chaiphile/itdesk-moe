import re


EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"\b\+?\d[\d\-\s()]{6,}\d\b")
CC_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
NID_RE = re.compile(r"\b(?:ssn|ssnumber|national[_ ]?id|nid)[:#\s]*([0-9\-]{6,20})\b", flags=re.IGNORECASE)
DIGIT_ID_RE = re.compile(r"\b\d{6,12}\b")
PERSONNEL_ID_RE = re.compile(r"\bEMP[_-]?\d{3,10}\b", flags=re.IGNORECASE)


def mask_pii(text: str) -> str:
    """Deterministic regex-based masker for emails, phones, IDs and similar.

    Replaces detected PII with the token [REDACTED_PII]. This is intentionally
    conservative and may over-mask; it's a defensive measure before sending
    data to third-party LLMs.
    """
    t = EMAIL_RE.sub("[REDACTED_PII]", text)
    t = PHONE_RE.sub("[REDACTED_PII]", t)
    t = CC_RE.sub("[REDACTED_PII]", t)
    t = NID_RE.sub("[REDACTED_PII]", t)
    t = PERSONNEL_ID_RE.sub("[REDACTED_PII]", t)
    # generic digit IDs as last resort (avoid masking short numbers like '2024')
    t = DIGIT_ID_RE.sub(lambda m: "[REDACTED_PII]" if len(m.group(0)) >= 6 else m.group(0), t)
    return t


def filter_attachments(messages):
    # messages: list of objects or dicts with 'type' and 'body'
    out = []
    for m in messages:
        mtype = None
        if isinstance(m, dict):
            mtype = m.get("type")
        else:
            mtype = getattr(m, "type", None)
        # defensive: treat any non-text type as non-sendable
        if mtype and str(mtype).lower() in ("attachment", "file", "object"):
            continue
        out.append(m)
    return out
