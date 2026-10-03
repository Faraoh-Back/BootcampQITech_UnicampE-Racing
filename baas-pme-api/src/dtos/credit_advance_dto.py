from models import CreditAdvance


class CreditAdvanceDTO:
    @staticmethod
    def obj_to_created_dict(credit_advance: CreditAdvance, bank_slip_keys: list[str], balance: int) -> dict:
        return {
            "credit_advance_key": credit_advance.credit_advance_key,
            "gross_amount": credit_advance.gross_amount,
            "fee_amount": credit_advance.fee_amount,
            "net_amount": credit_advance.net_amount,
            "balance": balance,
            "bank_slip_keys": bank_slip_keys,
            "created_at": credit_advance.created_at.isoformat(),
        }
