from sqlalchemy import Boolean, CHAR, BigInteger, Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, text

from models.base import Base


class RiskPolicy(Base):
    __tablename__ = "risk_policy"
    __table_args__ = (UniqueConstraint("customer_id", "version", name="unq_risk_customer_version"),)

    id = Column(Integer, primary_key=True)
    policy_key = Column(CHAR(36), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=True)
    version = Column(Integer, nullable=False)
    transfer_enabled = Column(Boolean, nullable=False, server_default=text("TRUE"))
    billing_plan_enabled = Column(Boolean, nullable=False, server_default=text("TRUE"))
    credit_advance_enabled = Column(Boolean, nullable=False, server_default=text("TRUE"))
    max_transfer_amount = Column(BigInteger, nullable=False)
    daily_outgoing_limit = Column(BigInteger, nullable=False)
    max_credit_advance_amount = Column(BigInteger, nullable=False)
    max_advance_bank_slips = Column(Integer, nullable=False)
    effective_from = Column(DateTime, nullable=False, server_default=text("NOW()"))
    effective_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))


class RiskPolicySnapshot(Base):
    __tablename__ = "risk_policy_snapshot"

    id = Column(Integer, primary_key=True)
    policy_key = Column(CHAR(36), nullable=False)
    policy_version = Column(Integer, nullable=False)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=True)
    operation = Column(String(40), nullable=False)
    transfer_enabled = Column(Boolean, nullable=False)
    billing_plan_enabled = Column(Boolean, nullable=False)
    credit_advance_enabled = Column(Boolean, nullable=False)
    max_transfer_amount = Column(BigInteger, nullable=False)
    daily_outgoing_limit = Column(BigInteger, nullable=False)
    max_credit_advance_amount = Column(BigInteger, nullable=False)
    max_advance_bank_slips = Column(Integer, nullable=False)
    requested_amount = Column(BigInteger, nullable=False, server_default=text("0"))
    requested_bank_slips = Column(Integer, nullable=False, server_default=text("0"))
    daily_outgoing_before = Column(BigInteger, nullable=True)
    daily_outgoing_after = Column(BigInteger, nullable=True)
    applied_at = Column(DateTime, nullable=False, server_default=text("NOW()"))


class CustomerDailyOutgoing(Base):
    __tablename__ = "customer_daily_outgoing"

    customer_id = Column(Integer, ForeignKey("customer.id"), primary_key=True)
    operation_date = Column(Date, primary_key=True)
    consumed_amount = Column(BigInteger, nullable=False, server_default=text("0"))
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
