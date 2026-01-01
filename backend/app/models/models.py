from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    permissions = Column(Text, nullable=True)  # JSON string or comma-separated permissions

    # Relationships
    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    # Organization unit association and scope
    org_unit_id = Column(Integer, ForeignKey("org_units.id"), nullable=True, index=True)
    scope_level = Column(String, nullable=False, default="SELF")
    role_id = Column(Integer, ForeignKey("roles.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    role = relationship("Role", back_populates="users")
    org_unit = relationship("OrgUnit")
    tickets = relationship("Ticket", back_populates="user")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    status = Column(String, default="open")
    priority = Column(String, default="medium")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"))
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="tickets")
    team = relationship("Team", back_populates="tickets")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tickets = relationship("Ticket", back_populates="team")


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
