from sqlalchemy import Column, Integer, String, DateTime, CHAR, text
from src.models.base import Base

class Customer(Base):
    __tablename__ = "customer"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_key = Column(CHAR(36), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    document_number = Column(String(18), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))