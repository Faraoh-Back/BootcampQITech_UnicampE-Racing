from dataclasses import dataclass

from controllers.base_controller import BaseController
from controllers.idempotency_controller import IdempotencyController
from dtos import TransactionDTO
from errors import (
    AccountNotApproved,
    AccountNotFound,
    InsufficientBalance,
    InvalidSchema,
    TransactionNotFound,
)
from repositories import AccountRepository, TransactionRepository


@dataclass(frozen=True)
class TransactionExecution:
    body: dict
    replayed: bool = False


class TransactionController(BaseController):
    """Depósitos e saques; transferências entram na S5.

    A conta é travada antes de consultar saldo e status. Dessa forma duas
    requisições de saque não leem o mesmo saldo simultaneamente, e o CHECK
    ``balance >= 0`` no banco permanece como a última barreira de segurança.
    """

    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.transaction_repository = TransactionRepository(self.context)
        self.idempotency_controller = IdempotencyController(self.context)

    def create(self, account_key: str, payload: dict, idempotency_key: str) -> TransactionExecution:
        # O JSON Schema considera 10.0 como integer; no domínio monetário
        # somente o tipo inteiro do JSON é aceito.
        if type(payload["amount"]) is not int:
            raise InvalidSchema("amount must be an integer amount in cents.")

        # A chave é registrada antes da trava da conta. Se houver duas
        # requisições iguais, o UNIQUE do PostgreSQL faz a segunda aguardar
        # a confirmação da primeira e então receber o replay, sem disputar
        # o saldo ou criar um segundo lançamento.
        account = self.account_repository.get_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)

        idempotency = self.idempotency_controller.begin(
            account.id, "transaction", idempotency_key, payload
        )
        if idempotency.should_replay:
            return TransactionExecution(body=idempotency.response_body, replayed=True)

        account = self.account_repository.get_by_key_for_update(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        if account.status.enumerator != "APPROVED":
            raise AccountNotApproved(account_key)

        transaction_type = payload["type"]
        if transaction_type == "DEPOSIT":
            signed_amount = payload["amount"]
        elif transaction_type == "WITHDRAWAL":
            if account.balance < payload["amount"]:
                raise InsufficientBalance(account_key)
            signed_amount = -payload["amount"]
        else:
            # O schema garante que TRANSFER tenha destino. Sua movimentação
            # de duas contas e tarifa é deliberadamente entregue na S5.
            raise InvalidSchema("TRANSFER is not available until the transfer operation is implemented.")

        transaction = self.transaction_repository.create_entry(
            account, transaction_type, signed_amount
        )
        transaction_dto = TransactionDTO.obj_to_created_dict(transaction)
        self.idempotency_controller.store_response(idempotency.record, 201, transaction_dto)
        self.session.commit()
        return TransactionExecution(body=transaction_dto)

    def get_by_key(self, account_key: str, transaction_key: str) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        transaction = self.transaction_repository.get_by_key_for_account(account.id, transaction_key)
        if transaction is None:
            raise TransactionNotFound()
        return TransactionDTO.obj_to_dict(transaction)

    def get_list(self, account_key: str, query_params: dict) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)

        limit = int(query_params.get("limit", 10))
        page = int(query_params.get("page", 0))
        transactions, is_last_page = self.transaction_repository.get_page(
            account.id, limit, page, query_params.get("type")
        )
        return {
            "data": [TransactionDTO.obj_to_dict(transaction) for transaction in transactions],
            "page": page,
            "limit": limit,
            "is_last_page": is_last_page,
        }
