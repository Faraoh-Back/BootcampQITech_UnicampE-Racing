from sqlalchemy import Column, Integer, BigInteger, DateTime, CHAR, ForeignKey, text
from src.models.base import Base

class CreditAdvance(Base):
    __tablename__ = "credit_advance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    credit_advance_key = Column(CHAR(36), nullable=False, unique=True)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    gross_amount = Column(BigInteger, nullable=False)
    fee_amount = Column(BigInteger, nullable=False)
    net_amount = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))