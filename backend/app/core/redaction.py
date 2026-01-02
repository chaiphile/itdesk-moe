"""Redaction rules and engine for sensitive attachment metadata.

This module provides functionality to redact sensitive information from
attachment metadata before exporting tickets and their attachments.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime


class RedactionRule:
    """Represents a rule for redacting specific fields or patterns."""

    def __init__(self, field_path: str, rule_type: str = "mask"):
        """Initialize redaction rule.

        Args:
            field_path: Dot-separated path to the field (e.g., "ticket.description")
            rule_type: Type of redaction - "mask", "remove", "hash"
        """
        self.field_path = field_path
        self.rule_type = rule_type

    def apply(self, data: Dict[str, Any], value: Any) -> Any:
        """Apply the redaction rule to a value."""
        if self.rule_type == "mask":
            return self._mask_value(value)
        elif self.rule_type == "remove":
            return None
        elif self.rule_type == "hash":
            return self._hash_value(value)
        return value

    def _mask_value(self, value: Any) -> str:
        """Replace sensitive value with redacted indicator."""
        if isinstance(value, str):
            if len(value) <= 4:
                return "[REDACTED]"
            return value[:2] + "*" * (len(value) - 4) + value[-2:]
        return "[REDACTED]"

    def _hash_value(self, value: Any) -> str:
        """Hash a sensitive value."""
        import hashlib
        if isinstance(value, str):
            return hashlib.sha256(value.encode()).hexdigest()[:16]
        return "[REDACTED]"


class RedactionRuleset:
    """Collection of redaction rules organized by sensitivity level."""

    def __init__(self):
        self.rules_by_level: Dict[str, List[RedactionRule]] = {
            "REGULAR": [],
            "CONFIDENTIAL": [
                RedactionRule("ticket.title", "mask"),
                RedactionRule("ticket.description", "mask"),
            ],
            "RESTRICTED": [
                RedactionRule("ticket.title", "remove"),
                RedactionRule("ticket.description", "remove"),
                RedactionRule("attachment.original_filename", "mask"),
            ],
        }

    def get_rules_for_level(self, sensitivity_level: str) -> List[RedactionRule]:
        """Get all redaction rules for a sensitivity level."""
        return self.rules_by_level.get(sensitivity_level, [])


class RedactionEngine:
    """Engine for applying redaction rules to data structures."""

    def __init__(self, ruleset: Optional[RedactionRuleset] = None):
        self.ruleset = ruleset or RedactionRuleset()

    def redact_attachment_metadata(
        self, attachment_data: Dict[str, Any], sensitivity_level: str = "REGULAR"
    ) -> Dict[str, Any]:
        """Redact attachment metadata based on sensitivity level.

        Args:
            attachment_data: Attachment metadata dict
            sensitivity_level: Sensitivity level (REGULAR, CONFIDENTIAL, RESTRICTED)

        Returns:
            Redacted copy of the metadata
        """
        redacted = attachment_data.copy()
        rules = self.ruleset.get_rules_for_level(sensitivity_level)

        # Apply attachment-specific redactions
        if sensitivity_level == "CONFIDENTIAL":
            if "original_filename" in redacted:
                redacted["original_filename"] = self._mask_filename(
                    redacted["original_filename"]
                )
        elif sensitivity_level == "RESTRICTED":
            if "original_filename" in redacted:
                redacted["original_filename"] = "[REDACTED FILE]"
            if "size" in redacted:
                redacted["size"] = None  # Hide file size for restricted

        return redacted

    def redact_ticket_export(
        self, ticket_data: Dict[str, Any], has_export_permission: bool = False
    ) -> Dict[str, Any]:
        """Redact ticket data for export based on permissions.

        Args:
            ticket_data: Complete ticket data including attachments
            has_export_permission: Whether user has explicit export permission

        Returns:
            Redacted copy of ticket data
        """
        redacted = ticket_data.copy()

        # If user doesn't have export permission, apply standard redactions
        if not has_export_permission:
            sensitivity = ticket_data.get("sensitivity_level", "REGULAR")
            rules = self.ruleset.get_rules_for_level(sensitivity)

            for rule in rules:
                if rule.field_path.startswith("ticket."):
                    field = rule.field_path.split(".")[-1]
                    if field in redacted:
                        redacted[field] = rule.apply(redacted, redacted[field])

        # Filter and redact attachments
        if "attachments" in redacted:
            redacted["attachments"] = self._redact_attachments(
                redacted["attachments"], has_export_permission
            )

        return redacted

    def _redact_attachments(
        self, attachments: List[Dict[str, Any]], has_export_permission: bool
    ) -> List[Dict[str, Any]]:
        """Redact attachment list based on sensitivity and permissions.

        Args:
            attachments: List of attachment metadata
            has_export_permission: Whether user can export all attachments

        Returns:
            Filtered and redacted attachments
        """
        result = []
        for att in attachments:
            # Filter out RESTRICTED attachments unless user has permission
            if att.get("sensitivity_level") == "RESTRICTED" and not has_export_permission:
                continue

            # Redact metadata
            sensitivity = att.get("sensitivity_level", "REGULAR")
            redacted_att = self.redact_attachment_metadata(att, sensitivity)
            result.append(redacted_att)

        return result

    def _mask_filename(self, filename: str) -> str:
        """Mask a filename while preserving extension."""
        if "." not in filename:
            return "[REDACTED]"

        parts = filename.rsplit(".", 1)
        name, ext = parts[0], parts[1]

        # Show first char and extension only
        masked_name = name[0] + "*" * (len(name) - 1) if len(name) > 1 else "*"
        return f"{masked_name}.{ext}"


def create_redaction_engine() -> RedactionEngine:
    """Factory function to create and initialize a redaction engine."""
    return RedactionEngine()
