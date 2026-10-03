from datetime import datetime
from uuid import uuid4

from database import Context
from models import Account, AccountStatus, AccountStatusEvent, Customer


class AccountRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, customer: Customer) -> Account:
        pending_status = self.get_status("PENDING")
        account = Account(
            account_key=str(uuid4()),
            customer=customer,
            status=pending_status,
            balance=0,
        )
        self.session.add(account)
        self.session.flush()
        self._append_status_event(account, pending_status)
        return account

    def get_by_key(self, account_key: str) -> Account | None:
        return self.session.query(Account).filter(Account.account_key == account_key).first()

    def get_by_key_for_update(self, account_key: str) -> Account | None:
        return (
            self.session.query(Account)
            # A conta pode já ter sido lida para reservar a chave de
            # idempotência. Depois de esperar outra transação liberar o
            # FOR UPDATE, a identidade em memória estaria obsoleta sem este
            # refresh e o saldo seria validado com um valor antigo.
            .populate_existing()
            .filter(Account.account_key == account_key)
            # FOR NO KEY UPDATE continua exclusivo para mudanças de saldo e
            # status, mas não conflita com o KEY SHARE que a FK da reserva de
            # idempotência acabou de criar na mesma conta.
            .with_for_update(key_share=True)
            .first()
        )

    def get_by_keys_for_update(self, account_keys: list[str]) -> list[Account]:
        return (
            self.session.query(Account)
            .populate_existing()
            .filter(Account.account_key.in_(account_keys))
            .order_by(Account.id.asc())
            .with_for_update(key_share=True)
            .all()
        )

    def get_customer_by_key(self, customer_key: str) -> Customer | None:
        return self.session.query(Customer).filter(Customer.customer_key == customer_key).first()

    def update_status(self, account: Account, status_enumerator: str) -> None:
        status = self.get_status(status_enumerator)
        account.status = status
        self._append_status_event(account, status)

    def get_status(self, enumerator: str) -> AccountStatus:
        return self.session.query(AccountStatus).filter(AccountStatus.enumerator == enumerator).one()

    def _append_status_event(self, account: Account, status: AccountStatus) -> None:
        account.status_events.append(
            AccountStatusEvent(status=status, event_datetime=datetime.utcnow())
        )
