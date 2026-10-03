from datetime import date
from uuid import uuid4

from connectors import BankSlipConnector
from controllers.base_controller import BaseController
from dtos import BillingPlanDTO
from errors import (
    AccountNotApproved,
    AccountNotFound,
    BillingPlanNotFound,
    ExternalConnectorError,
    InvalidFirstDueDate,
    InvalidSchema,
)
from repositories import BillingPlanRepository
from utils.date import add_months


class BillingPlanController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.billing_plan_repository = BillingPlanRepository(self.context)

    def create(self, account_key: str, payload: dict) -> dict:
        account = self.billing_plan_repository.get_account_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        if account.status.enumerator != "APPROVED":
            raise AccountNotApproved(account_key)

        try:
            first_due_date = date.fromisoformat(payload["first_due_date"])
        except ValueError as error:
            raise InvalidSchema("first_due_date must be a real date in YYYY-MM-DD format.") from error
        if first_due_date < date.today():
            raise InvalidFirstDueDate(payload["first_due_date"])

        plan_key = str(uuid4())
        installments = self._build_installments(payload["base_amount"], first_due_date)
        issued_by_installment = self._issue_batch(plan_key, installments)
        issued_slips = [
            {**installment, "barcode": issued_by_installment[installment["installment_number"]]}
            for installment in installments
        ]

        plan = self.billing_plan_repository.create(
            account, plan_key, payload["base_amount"], first_due_date, issued_slips
        )
        plan_dto = BillingPlanDTO.obj_to_created_dict(plan)
        self.session.commit()
        return plan_dto

    def get_by_key(self, account_key: str, plan_key: str) -> dict:
        account = self.billing_plan_repository.get_account_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        plan = self.billing_plan_repository.get_by_key_for_account(plan_key, account.id)
        if plan is None:
            raise BillingPlanNotFound(plan_key)
        return BillingPlanDTO.obj_to_dict(plan)

    @staticmethod
    def _build_installments(base_amount: int, first_due_date: date) -> list[dict]:
        return [
            {
                "installment_number": installment_number,
                "amount": base_amount,
                "due_date": add_months(first_due_date, installment_number - 1),
            }
            for installment_number in range(1, 13)
        ]

    @staticmethod
    def _issue_batch(plan_key: str, installments: list[dict]) -> dict[int, str]:
        response = BankSlipConnector().issue_batch(
            external_reference=f"{plan_key}:batch:1",
            installments=[
                {**installment, "due_date": installment["due_date"].isoformat()}
                for installment in installments
            ],
        )
        expected_numbers = {installment["installment_number"] for installment in installments}
        response_numbers = [bank_slip["installment_number"] for bank_slip in response]
        if len(response) != len(expected_numbers) or set(response_numbers) != expected_numbers:
            raise ExternalConnectorError(BankSlipConnector.__name__)
        return {bank_slip["installment_number"]: bank_slip["barcode"] for bank_slip in response}
