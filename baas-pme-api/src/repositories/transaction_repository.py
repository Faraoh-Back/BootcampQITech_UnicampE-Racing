from uuid import uuid4

from database import Context
from models import Account, Transaction


class TransactionRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create_entry(self, account: Account, transaction_type: str, signed_amount: int) -> Transaction:
        """Acrescenta uma linha imutável ao ledger e atualiza o cache de saldo.

        O controller já travou a conta e confirmou as regras de negócio.
        Ambos os efeitos ficam na mesma sessão e são confirmados uma vez pelo
        controller, portanto não há saldo sem lançamento nem lançamento sem saldo.
        """
        balance_after = account.balance + signed_amount
        transaction = Transaction(
            transaction_key=str(uuid4()),
            operation_key=str(uuid4()),
            account_id=account.id,
            type=transaction_type,
            amount=signed_amount,
            balance_after=balance_after,
        )
        account.balance = balance_after
        self.session.add(transaction)
        self.session.flush()
        return transaction
