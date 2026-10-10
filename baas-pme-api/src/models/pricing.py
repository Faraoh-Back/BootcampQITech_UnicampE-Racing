from sqlalchemy import CHAR, BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from models.base import Base


class PricingPolicy(Base):
    __tablename__ = "pricing_policy"
    __table_args__ = (
        UniqueConstraint("customer_id", "operation", "version", name="unq_pricing_customer_operation_version"),
    )

    id = Column(Integer, primary_key=True)
    policy_key = Column(CHAR(36), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=True)
    operation = Column(String(40), nullable=False)
    version = Column(Integer, nullable=False)
    fixed_fee_cents = Column(BigInteger, nullable=False, server_default=text("0"))
    percentage_basis_points = Column(Integer, nullable=False, server_default=text("0"))
    effective_from = Column(DateTime, nullable=False, server_default=text("NOW()"))
    effective_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))


class PricingSnapshot(Base):
    __tablename__ = "pricing_snapshot"

    id = Column(Integer, primary_key=True)
    policy_key = Column(CHAR(36), nullable=False)
    policy_version = Column(Integer, nullable=False)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=True)
    operation = Column(String(40), nullable=False)
    fixed_fee_cents = Column(BigInteger, nullable=False)
    percentage_basis_points = Column(Integer, nullable=False)
    base_amount = Column(BigInteger, nullable=False)
    fee_amount = Column(BigInteger, nullable=False)
    applied_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

