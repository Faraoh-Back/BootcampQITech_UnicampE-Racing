from uuid import uuid4

from database import Context
from models import BankSlip, BillingPlan, CreditAdvance


class CreditAdvanceRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_bank_slips_for_account_for_update(
        self, account_id: int, bank_slip_keys: list[str]
    ) -> list[BankSlip]:
        """Trava os recebíveis em ordem estável, sem vazar boletos alheios."""
        return (
            self.session.query(BankSlip)
            .join(BillingPlan)
            .filter(
                BillingPlan.account_id == account_id,
                BankSlip.bank_slip_key.in_(bank_slip_keys),
            )
            .order_by(BankSlip.id.asc())
            .with_for_update()
            .all()
        )

    def create(self, account_id: int, gross_amount: int, fee_amount: int) -> CreditAdvance:
        credit_advance = CreditAdvance(
            credit_advance_key=str(uuid4()),
            account_id=account_id,
            gross_amount=gross_amount,
            fee_amount=fee_amount,
            net_amount=gross_amount - fee_amount,
        )
        self.session.add(credit_advance)
        self.session.flush()
        return credit_advance
