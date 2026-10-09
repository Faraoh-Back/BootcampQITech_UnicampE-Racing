from sqlalchemy import CHAR, Column, DateTime, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class AuditEvent(Base):
    """Registro imutável de uma mudança de domínio, encadeado por hash."""

    __tablename__ = "audit_event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_type = Column(String(20), nullable=False)
    actor_key = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    resource_type = Column(String(64), nullable=False)
    resource_key = Column(CHAR(36), nullable=False)
    request_id = Column(String(64), nullable=False)
    origin = Column(String(255), nullable=False)
    previous_summary = Column(JSONB, nullable=True)
    current_summary = Column(JSONB, nullable=True)
    previous_hash = Column(CHAR(64), nullable=False)
    event_hash = Column(CHAR(64), nullable=False, unique=True)
    event_datetime = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
