from uuid import uuid4

from database import Context
from models import Account, Transaction


class TransactionRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create_entry(
        self,
        account: Account,
        transaction_type: str,
        signed_amount: int,
        operation_key: str | None = None,
        counterparty_account_id: int | None = None,
        pricing_snapshot_id: int | None = None,
        risk_policy_snapshot_id: int | None = None,
    ) -> Transaction:
        """Acrescenta uma linha imutável ao ledger e atualiza o cache de saldo.

        O controller já travou a conta e confirmou as regras de negócio.
        Ambos os efeitos ficam na mesma sessão e são confirmados uma vez pelo
        controller, portanto não há saldo sem lançamento nem lançamento sem saldo.
        """
        balance_after = account.balance + signed_amount
        transaction = Transaction(
            transaction_key=str(uuid4()),
            operation_key=operation_key or str(uuid4()),
            account_id=account.id,
            counterparty_account_id=counterparty_account_id,
            type=transaction_type,
            amount=signed_amount,
            balance_after=balance_after,
            pricing_snapshot_id=pricing_snapshot_id,
            risk_policy_snapshot_id=risk_policy_snapshot_id,
        )
        account.balance = balance_after
        self.session.add(transaction)
        self.session.flush()
        return transaction

    def get_by_key_for_account(self, account_id: int, transaction_key: str) -> Transaction | None:
        return (
            self.session.query(Transaction)
            .filter(
                Transaction.account_id == account_id,
                Transaction.transaction_key == transaction_key,
            )
            .first()
        )

    def get_page(
        self, account_id: int, limit: int, page: int, transaction_type: str | None = None
    ) -> tuple[list[Transaction], bool]:
        """Busca uma linha extra para saber se há outra página sem COUNT."""
        query = self.session.query(Transaction).filter(Transaction.account_id == account_id)
        if transaction_type is not None:
            query = query.filter(Transaction.type == transaction_type)

        rows = (
            query.order_by(Transaction.created_at.desc(), Transaction.id.desc())
            .offset(page * limit)
            .limit(limit + 1)
            .all()
        )
        # Sem a linha extra, esta é a última página (inclusive o extrato
        # vazio). A linha extra existe apenas para responder isso sem COUNT.
        return rows[:limit], len(rows) <= limit
