from sqlalchemy import CHAR, BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, text

from models.base import Base


class Quote(Base):
    __tablename__ = "quote"
    __table_args__ = (
        CheckConstraint(
            "operation IN ('TRANSFER', 'BILLING_PLAN', 'CREDIT_ADVANCE')",
            name="chk_quote_operation",
        ),
        CheckConstraint(
            "gross_amount >= 0 AND fee_amount >= 0 AND net_amount >= 0",
            name="chk_quote_amounts",
        ),
        CheckConstraint(
            "operation <> 'CREDIT_ADVANCE' OR net_amount > 0",
            name="chk_quote_credit_advance_positive_net",
        ),
    )

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
