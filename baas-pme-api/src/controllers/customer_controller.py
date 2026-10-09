from controllers.base_controller import BaseController
from dtos import CustomerDTO
from errors import CustomerNotFound, DuplicatedDocumentNumber, DuplicatedEmail, InvalidDocumentNumber
from repositories import CustomerRepository
from sqlalchemy.exc import IntegrityError
from utils.document_number import is_valid_document_number


class CustomerController(BaseController):
    """Regras de cadastro e consulta de clientes PME."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.customer_repository = CustomerRepository(self.context)

    def create(self, payload: dict) -> dict:
        document_number = payload["document_number"]
        email = payload["email"]

        if not is_valid_document_number(document_number):
            raise InvalidDocumentNumber(document_number)

        if self.customer_repository.get_by_document_number(document_number) is not None:
            raise DuplicatedDocumentNumber(document_number)

        if self.customer_repository.get_by_email(email) is not None:
            raise DuplicatedEmail(email)

        try:
            customer = self.customer_repository.create(payload)
        except IntegrityError as error:
            # As consultas acima mantêm a ordem de erro previsível no fluxo
            # comum. Esta proteção cobre duas requisições concorrentes que
            # passaram por elas antes de uma delas gravar.
            self.session.rollback()
            if self.customer_repository.get_by_document_number(document_number) is not None:
                raise DuplicatedDocumentNumber(document_number) from error
            if self.customer_repository.get_by_email(email) is not None:
                raise DuplicatedEmail(email) from error
            raise

        customer_dto = CustomerDTO.only_obj_key(customer)
        self.audit.record(
            "CUSTOMER_CREATED",
            "CUSTOMER",
            customer.customer_key,
            current_summary={"customer_key": customer.customer_key},
        )
        self.session.commit()
        return customer_dto

    def get_by_key(self, customer_key: str) -> dict:
        customer = self.customer_repository.get_by_key(customer_key)
        if customer is None:
            raise CustomerNotFound(customer_key)
        return CustomerDTO.obj_to_dict(customer)
