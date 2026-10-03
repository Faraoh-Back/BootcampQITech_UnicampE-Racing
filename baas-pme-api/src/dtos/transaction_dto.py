from models import Transaction


class TransactionDTO:
    @staticmethod
    def obj_to_created_dict(transaction: Transaction) -> dict:
        return {
            "transaction_key": transaction.transaction_key,
            "type": transaction.type,
            "amount": abs(transaction.amount),
            "balance": transaction.balance_after,
            "created_at": transaction.created_at.isoformat(),
        }

    @staticmethod
    def obj_to_dict(transaction: Transaction) -> dict:
        result = {
            "transaction_key": transaction.transaction_key,
            "account_key": transaction.account.account_key,
            "type": transaction.type,
            "amount": transaction.amount,
            "balance_after": transaction.balance_after,
            "operation_key": transaction.operation_key,
            "created_at": transaction.created_at.isoformat(),
        }
        if transaction.counterparty_account is not None:
            result["counterparty_account_key"] = transaction.counterparty_account.account_key
        return result
