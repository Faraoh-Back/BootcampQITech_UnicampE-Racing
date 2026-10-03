from controllers.base_controller import BaseController
from dtos import TransactionDTO
from errors import AccountNotApproved, AccountNotFound, InsufficientBalance, InvalidSchema
from repositories import AccountRepository, TransactionRepository


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

    def create(self, account_key: str, payload: dict) -> dict:
        # O JSON Schema considera 10.0 como integer; no domínio monetário
        # somente o tipo inteiro do JSON é aceito.
        if type(payload["amount"]) is not int:
            raise InvalidSchema("amount must be an integer amount in cents.")

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
        self.session.commit()
        return transaction_dto
