from sqlalchemy import CHAR, BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import relationship
from models.base import Base

class Transaction(Base):
    __tablename__ = "transaction"
    __table_args__ = (
        CheckConstraint("amount <> 0", name="chk_transaction_amount_not_zero"),
        CheckConstraint(
            "type IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER_OUT', 'TRANSFER_IN', "
            "'TRANSFER_FEE', 'ADVANCE_CREDIT', 'ADVANCE_FEE')",
            name="chk_transaction_type",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_key = Column(CHAR(36), nullable=False, unique=True)
    operation_key = Column(CHAR(36), nullable=False)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    counterparty_account_id = Column(Integer, ForeignKey("account.id"), nullable=True)
    type = Column(String(20), nullable=False)
    amount = Column(BigInteger, nullable=False)
    balance_after = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

    account = relationship("Account", foreign_keys=[account_id])
    counterparty_account = relationship("Account", foreign_keys=[counterparty_account_id])
