from sqlalchemy import CHAR, BigInteger, CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import relationship
from models.base import Base

class BankSlipStatus(Base):
    __tablename__ = "bank_slip_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enumerator = Column(String(50), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

class BankSlip(Base):
    __tablename__ = "bank_slip"
    __table_args__ = (
        UniqueConstraint("billing_plan_id", "installment_number", name="unq_bank_slip_plan_installment"),
        CheckConstraint("amount <> 0", name="chk_bank_slip_amount_not_zero"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    bank_slip_key = Column("slip_key", CHAR(36), nullable=False, unique=True)
    billing_plan_id = Column(Integer, ForeignKey("billing_plan.id"), nullable=False)
    credit_advance_id = Column(Integer, ForeignKey("credit_advance.id"), nullable=True)
    status_id = Column(Integer, ForeignKey("bank_slip_status.id"), nullable=False)
    installment_number = Column(Integer, nullable=False)
    batch_number = Column(Integer, nullable=False, server_default=text("1"))
    adjustment_rate = Column(Numeric(12, 8), nullable=True)
    amount = Column(BigInteger, nullable=False)
    due_date = Column(Date, nullable=False)
    barcode = Column(String(60), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

    status = relationship("BankSlipStatus")
    status_events = relationship(
        "BankSlipStatusEvent",
        order_by="BankSlipStatusEvent.event_datetime.asc()",
        back_populates="bank_slip"
    )

class BankSlipStatusEvent(Base):
    __tablename__ = "bank_slip_status_event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bank_slip_id = Column(Integer, ForeignKey("bank_slip.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("bank_slip_status.id"), nullable=False)
    event_datetime = Column(DateTime, nullable=False, server_default=text("NOW()"))
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

    bank_slip = relationship("BankSlip", back_populates="status_events")
    status = relationship("BankSlipStatus")
