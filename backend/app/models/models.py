"""Database models for the application.

This file extends the existing lightweight ticket/team models to implement the
Ticket Core schema described in the task while keeping backward-compatible
column names where the DB already used legacy names (for example 'user_id').
"""

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    BigInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    permissions = Column(Text, nullable=True)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    org_unit_id = Column(Integer, ForeignKey("org_units.id"), nullable=True, index=True)
    scope_level = Column(String, nullable=False, default="SELF")
    role_id = Column(Integer, ForeignKey("roles.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    role = relationship("Role", back_populates="users")
    org_unit = relationship("OrgUnit")
    tickets = relationship(
        "Ticket",
        back_populates="created_by_user",
        foreign_keys=lambda: [Ticket.created_by],
        cascade="all, delete-orphan",
    )
    uploads = relationship(
        "Attachment",
        back_populates="uploader",
        foreign_keys=lambda: [Attachment.uploaded_by],
        cascade="all, delete-orphan",
    )


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    org_unit_id = Column(Integer, ForeignKey("org_units.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship(
        "TeamMember", back_populates="team", cascade="all, delete-orphan"
    )
    tickets = relationship("Ticket", back_populates="current_team")


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_in_team = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ux_team_members_team_user", "team_id", "user_id", unique=True),
    )

    team = relationship("Team", back_populates="members")
    user = relationship("User")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)

    # Map existing legacy column names to new attribute names where possible
    created_by = Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    owner_org_unit_id = Column(
        Integer, ForeignKey("org_units.id"), nullable=True, index=True
    )
    current_team_id = Column(
        "team_id", Integer, ForeignKey("teams.id"), nullable=True, index=True
    )
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    # Enums implemented as strings with CHECK constraints for portability
    priority = Column(String, nullable=False, server_default="MED")
    status = Column(String, nullable=False, server_default="OPEN")
    sensitivity_level = Column(String, nullable=False, server_default="REGULAR")

    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "priority IN ('LOW','MED','HIGH')", name="ck_tickets_priority_vals"
        ),
        CheckConstraint(
            "status IN ('OPEN','IN_PROGRESS','WAITING','RESOLVED','CLOSED')",
            name="ck_tickets_status_vals",
        ),
        CheckConstraint(
            "sensitivity_level IN ('REGULAR','CONFIDENTIAL')",
            name="ck_tickets_sensitivity_vals",
        ),
    )

    # Relationships
    created_by_user = relationship(
        "User", foreign_keys=[created_by], back_populates="tickets"
    )
    owner_org_unit = relationship("OrgUnit", foreign_keys=[owner_org_unit_id])
    current_team = relationship(
        "Team", foreign_keys=[current_team_id], back_populates="tickets"
    )
    assignee = relationship("User", foreign_keys=[assignee_id])
    category = relationship("Category")
    messages = relationship(
        "TicketMessage", back_populates="ticket", cascade="all, delete-orphan"
    )
    attachments = relationship(
        "Attachment", back_populates="ticket", cascade="all, delete-orphan"
    )

    # Backwards-compatible attribute names used by older tests/code
    @property
    def user_id(self):
        return self.created_by

    @user_id.setter
    def user_id(self, value):
        self.created_by = value

    @property
    def team_id(self):
        return self.current_team_id

    @team_id.setter
    def team_id(self, value):
        self.current_team_id = value

    # compatibility relationship names
    @property
    def user(self):
        return self.created_by_user

    @property
    def team(self):
        return self.current_team


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False, server_default="PUBLIC")
    body = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "type IN ('PUBLIC','INTERNAL')", name="ck_ticket_messages_type_vals"
        ),
        Index("idx_ticket_messages_ticket_id_created_at", "ticket_id", "created_at"),
    )

    ticket = relationship("Ticket", back_populates="messages")
    author = relationship("User")


class OrgUnit(Base):
    __tablename__ = "org_units"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("org_units.id"), nullable=True, index=True)
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    path = Column(Text, nullable=False, default="")
    depth = Column(Integer, nullable=False, default=0)

    parent = relationship("OrgUnit", remote_side=[id], backref="children")

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<OrgUnit id={self.id} name={self.name} path={self.path}>"


# Additional indexes for tickets
Index("idx_tickets_owner_org_unit_id", Ticket.owner_org_unit_id)
Index("idx_tickets_status", Ticket.status)
Index("idx_tickets_current_team_id", Ticket.current_team_id)
Index("idx_tickets_created_at", Ticket.created_at)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=True)
    diff_json = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    meta_json = Column(JSON, nullable=True)


# Indexes for audit logs
Index("idx_audit_logs_created_at", AuditLog.created_at)
Index("idx_audit_logs_actor_id", AuditLog.actor_id)
Index("idx_audit_logs_entity", AuditLog.entity_type, AuditLog.entity_id)


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    object_key = Column(String, nullable=False, unique=True, index=True)
    original_filename = Column(String, nullable=False)
    mime = Column(String, nullable=True)
    size = Column(BigInteger, nullable=False)
    checksum = Column(String, nullable=True)
    scanned_status = Column(String, nullable=False, server_default="PENDING")
    scanned_at = Column(DateTime(timezone=True), nullable=True)
    sensitivity_level = Column(String, nullable=False, server_default="REGULAR")
    retention_days = Column(Integer, nullable=True)
    status = Column(String, nullable=False, server_default="ACTIVE")
    redacted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        CheckConstraint(
            "scanned_status IN ('PENDING','CLEAN','INFECTED','FAILED')",
            name="ck_attachments_scanned_status_vals",
        ),
        CheckConstraint(
            "sensitivity_level IN ('REGULAR','CONFIDENTIAL','RESTRICTED')",
            name="ck_attachments_sensitivity_vals",
        ),
        CheckConstraint(
            "status IN ('ACTIVE','DELETED')",
            name="ck_attachments_status_vals",
        ),
    )

    ticket = relationship("Ticket", back_populates="attachments")
    uploader = relationship("User", back_populates="uploads")


# Indexes for attachments
Index("idx_attachments_ticket_id", Attachment.ticket_id)
Index("idx_attachments_scanned_status", Attachment.scanned_status)
