from dataclasses import dataclass
from uuid import uuid4

from constants import NIGHT_LIMIT_CENTS, TRANSFER_FEE_CENTS
from controllers.base_controller import BaseController
from controllers.idempotency_controller import IdempotencyController
from dtos import TransactionDTO
from errors import (
    AccountNotApproved,
    AccountNotFound,
    InsufficientBalance,
    InvalidSchema,
    NightLimitExceeded,
    SameAccountTransfer,
    TransactionNotFound,
)
from repositories import AccountRepository, TransactionRepository
from utils.night_limit import is_night_window


@dataclass(frozen=True)
class TransactionExecution:
    body: dict
    replayed: bool = False


class TransactionController(BaseController):
    """Movimenta saldo por lançamentos imutáveis no ledger.

    Para uma transferência as duas contas são travadas em ordem de ID antes
    de ler saldo e status. Isso também evita deadlock entre A→B e B→A.
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

        transaction_type = payload["type"]
        destination_account_key = payload.get("destination_account_key")

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

        if transaction_type == "TRANSFER" and destination_account_key == account_key:
            raise SameAccountTransfer()

        # A regra é avaliada antes de disputar a trava da conta. Um replay já
        # confirmado retorna acima, independente da hora em que foi reenviado.
        if (
            transaction_type in {"WITHDRAWAL", "TRANSFER"}
            and payload["amount"] > NIGHT_LIMIT_CENTS
            and is_night_window()
        ):
            raise NightLimitExceeded()

        if transaction_type == "TRANSFER":
            transaction_dto = self._create_transfer(
                account_key, destination_account_key, payload["amount"]
            )
        else:
            transaction_dto = self._create_single_account_transaction(
                account_key, transaction_type, payload["amount"]
            )
        self.idempotency_controller.store_response(idempotency.record, 201, transaction_dto)
        self.audit.record(
            f"{transaction_type}_CREATED",
            "TRANSACTION",
            transaction_dto["transaction_key"],
            current_summary={
                "account_key": account_key,
                "amount": transaction_dto["amount"],
                "balance": transaction_dto["balance"],
                "type": transaction_dto["type"],
            },
        )
        self.session.commit()
        return TransactionExecution(body=transaction_dto)

    def _create_single_account_transaction(
        self, account_key: str, transaction_type: str, amount: int
    ) -> dict:
        account = self.account_repository.get_by_key_for_update(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        if account.status.enumerator != "APPROVED":
            raise AccountNotApproved(account_key)

        if transaction_type == "DEPOSIT":
            signed_amount = amount
        else:
            if account.balance < amount:
                raise InsufficientBalance(account_key)
            signed_amount = -amount

        transaction = self.transaction_repository.create_entry(
            account, transaction_type, signed_amount
        )
        return TransactionDTO.obj_to_created_dict(transaction)

    def _create_transfer(
        self, origin_account_key: str, destination_account_key: str, amount: int
    ) -> dict:
        accounts = self.account_repository.get_by_keys_for_update(
            [origin_account_key, destination_account_key]
        )
        accounts_by_key = {account.account_key: account for account in accounts}
        origin = accounts_by_key.get(origin_account_key)
        destination = accounts_by_key.get(destination_account_key)
        if origin is None:
            raise AccountNotFound(origin_account_key)
        if destination is None:
            raise AccountNotFound(destination_account_key)
        if origin.status.enumerator != "APPROVED":
            raise AccountNotApproved(origin_account_key)
        if destination.status.enumerator != "APPROVED":
            raise AccountNotApproved(destination_account_key)

        total_debit = amount + TRANSFER_FEE_CENTS
        if origin.balance < total_debit:
            raise InsufficientBalance(origin_account_key)

        operation_key = str(uuid4())
        transfer_out = self.transaction_repository.create_entry(
            origin,
            "TRANSFER_OUT",
            -amount,
            operation_key,
            destination.id,
        )
        self.transaction_repository.create_entry(
            origin, "TRANSFER_FEE", -TRANSFER_FEE_CENTS, operation_key
        )
        self.transaction_repository.create_entry(
            destination,
            "TRANSFER_IN",
            amount,
            operation_key,
            origin.id,
        )
        return {
            **TransactionDTO.obj_to_created_dict(transfer_out),
            "type": "TRANSFER",
            "fee_amount": TRANSFER_FEE_CENTS,
            "balance": origin.balance,
        }

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
