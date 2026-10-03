from sqlalchemy import Column, Integer, String, DateTime, CHAR, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from src.models.base import Base

class IdempotencyKey(Base):
    __tablename__ = "idempotency_key"
    __table_args__ = (
        UniqueConstraint("account_id", "scope", "idempotency_key", name="unq_idempotency_account_scope_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    idempotency_key = Column(String(64), nullable=False)
    scope = Column(String(40), nullable=False)
    request_hash = Column(CHAR(64), nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))