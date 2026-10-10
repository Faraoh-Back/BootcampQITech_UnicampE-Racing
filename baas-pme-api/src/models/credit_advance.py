from sqlalchemy import CHAR, BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Integer, text
from sqlalchemy.orm import relationship
from models.base import Base

class CreditAdvance(Base):
    __tablename__ = "credit_advance"
    __table_args__ = (
        CheckConstraint("net_amount = gross_amount - fee_amount", name="chk_credit_advance_net_amount"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    credit_advance_key = Column(CHAR(36), nullable=False, unique=True)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    gross_amount = Column(BigInteger, nullable=False)
    fee_amount = Column(BigInteger, nullable=False)
    net_amount = Column(BigInteger, nullable=False)
    pricing_snapshot_id = Column(Integer, ForeignKey("pricing_snapshot.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

    account = relationship("Account")
    bank_slips = relationship("BankSlip", back_populates="credit_advance")
