from sqlalchemy import Column, Integer, BigInteger, Date, DateTime, CHAR, ForeignKey, text
from models.base import Base

class BillingPlan(Base):
    __tablename__ = "billing_plan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_key = Column(CHAR(36), nullable=False, unique=True)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    base_amount = Column(BigInteger, nullable=False)
    first_due_date = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
