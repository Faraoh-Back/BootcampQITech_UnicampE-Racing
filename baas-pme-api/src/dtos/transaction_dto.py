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
