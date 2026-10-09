from sqlalchemy import CHAR, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import relationship

from models.base import Base


class User(Base):
    __tablename__ = "app_user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_key = Column(CHAR(36), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

    customer_accesses = relationship("UserCustomerAccess", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")


class UserCustomerAccess(Base):
    __tablename__ = "user_customer_access"
    __table_args__ = (
        UniqueConstraint("user_id", "customer_id", name="unq_user_customer_access"),
        CheckConstraint(
            "role IN ('OWNER', 'OPERATOR', 'VIEWER')", name="chk_user_customer_role"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("app_user.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    role = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

    user = relationship("User", back_populates="customer_accesses")
    customer = relationship("Customer")


class UserSession(Base):
    __tablename__ = "user_session"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_key = Column(CHAR(36), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("app_user.id"), nullable=False)
    refresh_token_hash = Column(CHAR(64), nullable=False, unique=True)
    device_name = Column(String(100), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))

    user = relationship("User", back_populates="sessions")
