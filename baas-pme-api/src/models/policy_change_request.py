from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class PolicyChangeRequest(Base):
    __tablename__ = "policy_change_request"

    id = Column(Integer, primary_key=True)
    request_key = Column(CHAR(36), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    policy_type = Column(String(20), nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False)
    creator_user_id = Column(Integer, ForeignKey("app_user.id"), nullable=False)
    approver_user_id = Column(Integer, ForeignKey("app_user.id"), nullable=True)
    published_policy_key = Column(CHAR(36), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    retired_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
