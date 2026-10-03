from sqlalchemy import CHAR, BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Integer, text
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
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
