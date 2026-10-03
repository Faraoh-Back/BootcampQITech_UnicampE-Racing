from models import Account


class AccountDTO:
    @staticmethod
    def obj_to_created_dict(account: Account) -> dict:
        return {
            "account_key": account.account_key,
            "customer_key": account.customer.customer_key,
            "status": account.status.enumerator,
            "balance": account.balance,
            "created_at": account.created_at.isoformat(),
        }

    @staticmethod
    def obj_to_dict(account: Account) -> dict:
        account_dto = AccountDTO.obj_to_created_dict(account)
        account_dto["status_events"] = [
            {
                "status": status_event.status.enumerator,
                "event_datetime": status_event.event_datetime.isoformat(),
            }
            for status_event in account.status_events
        ]
        return account_dto

    @staticmethod
    def obj_to_status_change_dict(account: Account) -> dict:
        """Contrato enxuto das rotas de bloqueio e cancelamento."""
        latest_event = account.status_events[-1]
        return {
            "account_key": account.account_key,
            "status": account.status.enumerator,
            "updated_at": latest_event.event_datetime.isoformat(),
        }
