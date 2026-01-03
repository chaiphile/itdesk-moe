import re
from ai_gateway.masking import mask_pii


def test_mask_email_and_phone():
    text = "Contact john.doe@example.com or +1 (555) 123-4567"
    masked = mask_pii(text)
    assert "[REDACTED_PII]" in masked
    assert "john.doe@example.com" not in masked
    assert "+1 (555) 123-4567" not in masked


def test_mask_nid_and_personnel():
    text = "Employee EMP-12345 has national id NID: 123456789"
    masked = mask_pii(text)
    assert "EMP-12345" not in masked
    assert "123456789" not in masked
