from sqlalchemy import CHAR, Column, DateTime, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class OutboxEvent(Base):
    """Evento de integração persistido com o fato de domínio que o originou."""

    __tablename__ = "outbox_event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_key = Column(CHAR(36), nullable=False, unique=True)
    topic = Column(String(64), nullable=False)
    aggregate_type = Column(String(64), nullable=False)
    aggregate_key = Column(CHAR(36), nullable=False)
    payload = Column(JSONB, nullable=False)
    delivery_attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
    locked_until = Column(DateTime, nullable=True)
    lock_token = Column(CHAR(36), nullable=True)
    published_at = Column(DateTime, nullable=True)
    last_error = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
