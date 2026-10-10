from sqlalchemy import CHAR, BigInteger, Column, DateTime, ForeignKey, Integer, String, text

from models.base import Base


class Quote(Base):
    __tablename__ = "quote"

    id = Column(Integer, primary_key=True)
    quote_key = Column(CHAR(36), nullable=False, unique=True)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    operation = Column(String(40), nullable=False)
    request_hash = Column(CHAR(64), nullable=False)
    gross_amount = Column(BigInteger, nullable=False)
    fee_amount = Column(BigInteger, nullable=False)
    net_amount = Column(BigInteger, nullable=False)
    pricing_policy_key = Column(CHAR(36), nullable=False)
    pricing_version = Column(Integer, nullable=False)
    risk_policy_key = Column(CHAR(36), nullable=False)
    risk_version = Column(Integer, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
