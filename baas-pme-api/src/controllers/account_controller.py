from controllers.base_controller import BaseController
from dtos import AccountDTO
from errors import AccountNotFound, CustomerNotFound, InvalidAccountStatusTransition
from repositories import AccountRepository
from repositories.outbox_repository import OutboxRepository


class AccountController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.outbox_repository = OutboxRepository(self.session)

    def create(self, payload: dict) -> dict:
        customer = self.account_repository.get_customer_by_key(payload["customer_key"])
        if customer is None:
            raise CustomerNotFound(payload["customer_key"])

        account = self.account_repository.create(customer)
        self.account_repository.update_status(account, "APPROVED")
        self.session.flush()
        account_dto = AccountDTO.obj_to_created_dict(account)
        self.audit.record(
            "ACCOUNT_CREATED",
            "ACCOUNT",
            account.account_key,
            current_summary={
                "balance": account.balance,
                "customer_key": customer.customer_key,
                "status": account.status.enumerator,
            },
        )
        self.session.commit()
        return account_dto

    def get_by_key(self, account_key: str) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        return AccountDTO.obj_to_dict(account)

    def block(self, account_key: str) -> dict:
        return self._change_status(account_key, "BLOCKED", allowed_current_statuses={"APPROVED"})

    def cancel(self, account_key: str) -> dict:
        return self._change_status(
            account_key,
            "CANCELLED",
            allowed_current_statuses={"APPROVED", "BLOCKED"},
        )

    def _change_status(
        self, account_key: str, requested_status: str, allowed_current_statuses: set[str]
    ) -> dict:
        account = self.account_repository.get_by_key_for_update(account_key)
        if account is None:
            raise AccountNotFound(account_key)

        current_status = account.status.enumerator
        if current_status not in allowed_current_statuses:
            raise InvalidAccountStatusTransition(current_status, requested_status)

        self.account_repository.update_status(account, requested_status)
        self.session.flush()
        account_dto = AccountDTO.obj_to_status_change_dict(account)
        self.audit.record(
            f"ACCOUNT_{requested_status}",
            "ACCOUNT",
            account.account_key,
            previous_summary={"status": current_status},
            current_summary={"status": requested_status},
        )
        # O evento só existe se o status e a auditoria também confirmarem.
        # O worker o publicará depois do commit, nunca dentro desta requisição.
        self.outbox_repository.enqueue(
            "account.status_changed",
            "ACCOUNT",
            account.account_key,
            {
                "account_key": account.account_key,
                "customer_key": account.customer.customer_key,
                "previous_status": current_status,
                "status": requested_status,
            },
        )
        self.session.commit()
        return account_dto
