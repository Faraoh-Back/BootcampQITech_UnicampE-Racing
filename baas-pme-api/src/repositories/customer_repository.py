from uuid import uuid4

from database import Context
from models import Customer


class CustomerRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, payload: dict) -> Customer:
        customer = Customer(
            customer_key=str(uuid4()),
            name=payload["name"],
            email=payload["email"],
            document_number=payload["document_number"],
        )
        self.session.add(customer)
        self.session.flush()
        return customer

    def get_by_key(self, customer_key: str) -> Customer | None:
        return self.session.query(Customer).filter(Customer.customer_key == customer_key).first()

    def get_by_document_number(self, document_number: str) -> Customer | None:
        return self.session.query(Customer).filter(Customer.document_number == document_number).first()

    def get_by_email(self, email: str) -> Customer | None:
        return self.session.query(Customer).filter(Customer.email == email).first()
