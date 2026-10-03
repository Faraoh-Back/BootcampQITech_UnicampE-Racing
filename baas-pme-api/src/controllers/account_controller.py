from controllers.base_controller import BaseController
from dtos import AccountDTO
from errors import AccountNotFound, CustomerNotFound
from repositories import AccountRepository


class AccountController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)

    def create(self, payload: dict) -> dict:
        customer = self.account_repository.get_customer_by_key(payload["customer_key"])
        if customer is None:
            raise CustomerNotFound(payload["customer_key"])

        account = self.account_repository.create(customer)
        self.account_repository.update_status(account, "APPROVED")
        self.session.flush()
        account_dto = AccountDTO.obj_to_created_dict(account)
        self.session.commit()
        return account_dto

    def get_by_key(self, account_key: str) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        return AccountDTO.obj_to_dict(account)
