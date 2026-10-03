from datetime import datetime
from uuid import uuid4

from database import Context
from models import Account, BankSlip, BankSlipStatus, BankSlipStatusEvent, BillingPlan


class BillingPlanRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_account_by_key(self, account_key: str) -> Account | None:
        return self.session.query(Account).filter(Account.account_key == account_key).first()

    def get_by_key_for_account(self, plan_key: str, account_id: int) -> BillingPlan | None:
        return (
            self.session.query(BillingPlan)
            .filter(BillingPlan.plan_key == plan_key, BillingPlan.account_id == account_id)
            .first()
        )

    def create(
        self,
        account: Account,
        plan_key: str,
        base_amount: int,
        first_due_date,
        issued_slips: list[dict],
    ) -> BillingPlan:
        """Monta o lote inicial depois que o emissor externo já confirmou tudo."""
        pending_status = self.get_bank_slip_status("PENDING")
        plan = BillingPlan(
            plan_key=plan_key,
            account=account,
            base_amount=base_amount,
            first_due_date=first_due_date,
        )
        self.session.add(plan)
        self.session.flush()

        for issued_slip in issued_slips:
            bank_slip = BankSlip(
                bank_slip_key=str(uuid4()),
                billing_plan=plan,
                status=pending_status,
                installment_number=issued_slip["installment_number"],
                amount=issued_slip["amount"],
                due_date=issued_slip["due_date"],
                barcode=issued_slip["barcode"],
            )
            self.session.add(bank_slip)
            self.session.flush()
            bank_slip.status_events.append(
                BankSlipStatusEvent(status=pending_status, event_datetime=datetime.utcnow())
            )

        self.session.flush()
        return plan

    def get_bank_slip_status(self, enumerator: str) -> BankSlipStatus:
        return (
            self.session.query(BankSlipStatus)
            .filter(BankSlipStatus.enumerator == enumerator)
            .one()
        )
