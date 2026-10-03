from sqlalchemy import Column, Integer, String, BigInteger, DateTime, CHAR, ForeignKey, text
from src.models.base import Base

class Transaction(Base):
    __tablename__ = "transaction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_key = Column(CHAR(36), nullable=False, unique=True)
    operation_key = Column(CHAR(36), nullable=False)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    counterparty_account_id = Column(Integer, ForeignKey("account.id"), nullable=True)
    type = Column(String(20), nullable=False)
    amount = Column(BigInteger, nullable=False)
    balance_after = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))