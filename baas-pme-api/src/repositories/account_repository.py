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
            .filter(Account.account_key == account_key)
            .with_for_update()
            .first()
        )

    def get_by_keys_for_update(self, account_keys: list[str]) -> list[Account]:
        return (
            self.session.query(Account)
            .filter(Account.account_key.in_(account_keys))
            .order_by(Account.id.asc())
            .with_for_update()
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
