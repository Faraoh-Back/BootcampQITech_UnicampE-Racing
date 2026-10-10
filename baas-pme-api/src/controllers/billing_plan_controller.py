from datetime import date
import time
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from connectors import BankSlipConnector, CentralBankConnector
from controllers.base_controller import BaseController
from dtos import BillingPlanDTO
from errors import (
    AccountNotApproved,
    AccountNotFound,
    AdjustmentAlreadyApplied,
    BillingPlanNotFound,
    ExternalConnectorError,
    InvalidFirstDueDate,
    InvalidSchema,
    InsufficientBalance,
)
from repositories import AccountRepository, BillingPlanRepository, PricingRepository, RiskPolicyRepository, TransactionRepository
from utils.date import add_months
from utils.metrics import observe_lock_wait


class BillingPlanController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.billing_plan_repository = BillingPlanRepository(self.context)
        self.account_repository = AccountRepository(self.context)
        self.pricing_repository = PricingRepository(self.context)
        self.transaction_repository = TransactionRepository(self.context)
        self.risk_policy_repository = RiskPolicyRepository(self.context)

    def create(self, account_key: str, payload: dict) -> dict:
        account = self.billing_plan_repository.get_account_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        if account.status.enumerator != "APPROVED":
            raise AccountNotApproved(account_key)
        # Verificação antes do conector evita emitir externamente um produto
        # que a política atual da PME já proibiu.
        self.risk_policy_repository.assert_billing_plan_enabled(account.customer_id)

        try:
            first_due_date = date.fromisoformat(payload["first_due_date"])
        except ValueError as error:
            raise InvalidSchema("first_due_date must be a real date in YYYY-MM-DD format.") from error
        if first_due_date < date.today():
            raise InvalidFirstDueDate(payload["first_due_date"])

        plan_key = str(uuid4())
        installments = self._build_installments(payload["base_amount"], first_due_date)
        issued_by_installment = self._issue_batch(plan_key, 1, installments)
        issued_slips = [
            {**installment, "barcode": issued_by_installment[installment["installment_number"]]}
            for installment in installments
        ]

        # O emissor externo já confirmou o lote. A cobrança de serviço é
        # separada do valor que o pagador deve no boleto e só entra no ledger
        # depois de travar/reler o saldo atual da PME.
        account = self.account_repository.get_by_key_for_update(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        if account.status.enumerator != "APPROVED":
            raise AccountNotApproved(account_key)
        pricing = self.pricing_repository.resolve(
            account.customer_id, "BANK_SLIP_ISSUANCE", payload["base_amount"] * len(installments)
        )
        if account.balance < pricing.fee_amount:
            raise InsufficientBalance(account_key)
        risk_snapshot = self.risk_policy_repository.apply_billing_plan(
            account.customer_id, payload["base_amount"] * len(installments)
        )

        plan = self.billing_plan_repository.create(
            account, plan_key, payload["base_amount"], first_due_date, issued_slips,
            pricing_snapshot_id=pricing.id,
        )
        plan.issuance_fee_amount = pricing.fee_amount
        plan.issuance_pricing_snapshot_id = pricing.id
        plan.risk_policy_snapshot_id = risk_snapshot.id
        if pricing.fee_amount:
            self.transaction_repository.create_entry(
                account,
                "BANK_SLIP_ISSUANCE_FEE",
                -pricing.fee_amount,
                str(uuid4()),
                pricing_snapshot_id=pricing.id,
                risk_policy_snapshot_id=risk_snapshot.id,
            )
        plan_dto = BillingPlanDTO.obj_to_created_dict(plan)
        self.audit.record(
            "BILLING_PLAN_CREATED",
            "BILLING_PLAN",
            plan.plan_key,
            current_summary={
                "account_key": account_key,
                "base_amount": plan.base_amount,
                "batch_number": 1,
                "issuance_fee_amount": pricing.fee_amount,
                "pricing_policy_key": pricing.policy_key,
                "pricing_policy_version": pricing.policy_version,
                "risk_policy_key": risk_snapshot.policy_key,
                "risk_policy_version": risk_snapshot.policy_version,
            },
        )
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

    def create_adjustment(self, account_key: str, plan_key: str, payload: dict) -> dict:
        account = self.billing_plan_repository.get_account_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        self.risk_policy_repository.assert_billing_plan_enabled(account.customer_id)
        plan = self.billing_plan_repository.get_by_key_for_account(plan_key, account.id)
        if plan is None:
            raise BillingPlanNotFound(plan_key)

        # A consulta externa acontece antes da trava: planos distintos e até
        # leituras repetidas do mesmo plano não devem prender uma transação.
        rate = CentralBankConnector().get_accumulated_rate(payload["index_code"])

        started_at = time.perf_counter()
        plan = self.billing_plan_repository.get_by_key_for_account_for_update(plan_key, account.id)
        observe_lock_wait("billing_plan", time.perf_counter() - started_at)
        if plan is None:
            raise BillingPlanNotFound(plan_key)
        if self.billing_plan_repository.has_batch(plan.id, 2):
            raise AdjustmentAlreadyApplied()

        adjusted_amount = self._adjust_amount(plan.base_amount, rate)
        installments = self._build_installments(
            adjusted_amount, plan.first_due_date, first_installment_number=13
        )
        issued_by_installment = self._issue_batch(plan.plan_key, 2, installments)
        issued_slips = [
            {**installment, "barcode": issued_by_installment[installment["installment_number"]]}
            for installment in installments
        ]
        # O lote reajustado também é uma emissão de boleto e, portanto, usa
        # a política vigente no momento da operação, não a tarifa histórica
        # do lote inicial.
        account = self.account_repository.get_by_key_for_update(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        if account.status.enumerator != "APPROVED":
            raise AccountNotApproved(account_key)
        pricing = self.pricing_repository.resolve(
            account.customer_id, "BANK_SLIP_ISSUANCE", adjusted_amount * len(installments)
        )
        if account.balance < pricing.fee_amount:
            raise InsufficientBalance(account_key)
        risk_snapshot = self.risk_policy_repository.apply_billing_plan(
            account.customer_id, adjusted_amount * len(installments)
        )
        bank_slips = self.billing_plan_repository.create_adjustment_batch(
            plan, rate, issued_slips, pricing_snapshot_id=pricing.id
        )
        if pricing.fee_amount:
            self.transaction_repository.create_entry(
                account, "BANK_SLIP_ISSUANCE_FEE", -pricing.fee_amount, str(uuid4()),
                pricing_snapshot_id=pricing.id,
                risk_policy_snapshot_id=risk_snapshot.id,
            )
        self.audit.record(
            "BILLING_PLAN_ADJUSTED",
            "BILLING_PLAN",
            plan.plan_key,
            previous_summary={"batch_number": 1, "base_amount": plan.base_amount},
            current_summary={
                "adjusted_amount": adjusted_amount,
                "batch_number": 2,
                "index_code": payload["index_code"],
                "rate": str(rate),
                "issuance_fee_amount": pricing.fee_amount,
                "pricing_policy_key": pricing.policy_key,
                "pricing_policy_version": pricing.policy_version,
                "risk_policy_key": risk_snapshot.policy_key,
                "risk_policy_version": risk_snapshot.policy_version,
            },
        )
        self.session.commit()
        return {
            "plan_key": plan.plan_key,
            "index_code": payload["index_code"],
            "accumulated_rate": str(rate),
            "adjusted_amount": adjusted_amount,
            "bank_slips": [BillingPlanDTO._bank_slip_to_dict(slip) for slip in bank_slips],
        }

    @staticmethod
    def _build_installments(
        base_amount: int, first_due_date: date, first_installment_number: int = 1
    ) -> list[dict]:
        return [
            {
                "installment_number": installment_number,
                "amount": base_amount,
                "due_date": add_months(first_due_date, installment_number - 1),
            }
            for installment_number in range(first_installment_number, first_installment_number + 12)
        ]

    @staticmethod
    def _adjust_amount(base_amount: int, rate: Decimal) -> int:
        factor = Decimal("1") + (rate / Decimal("100"))
        return int((Decimal(base_amount) * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _issue_batch(plan_key: str, batch_number: int, installments: list[dict]) -> dict[int, str]:
        response = BankSlipConnector().issue_batch(
            external_reference=f"{plan_key}:batch:{batch_number}",
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
