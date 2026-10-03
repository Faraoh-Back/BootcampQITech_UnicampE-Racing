from sqlalchemy import CHAR, BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import relationship
from models.base import Base

class AccountStatus(Base):
    __tablename__ = "account_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enumerator = Column(String(50), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

class Account(Base):
    __tablename__ = "account"
    __table_args__ = (CheckConstraint("balance >= 0", name="chk_account_balance_non_negative"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_key = Column(CHAR(36), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("account_status.id"), nullable=False)
    balance = Column(BigInteger, nullable=False, server_default=text("0"))
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

    customer = relationship("Customer")
    status = relationship("AccountStatus")
    status_events = relationship(
        "AccountStatusEvent",
        order_by="AccountStatusEvent.event_datetime.asc()",
        back_populates="account"
    )

class AccountStatusEvent(Base):
    __tablename__ = "account_status_event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("account_status.id"), nullable=False)
    event_datetime = Column(DateTime, nullable=False, server_default=text("NOW()"))
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

    account = relationship("Account", back_populates="status_events")
    status = relationship("AccountStatus")
