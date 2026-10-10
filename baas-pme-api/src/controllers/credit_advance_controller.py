from uuid import uuid4
import time

from controllers.base_controller import BaseController
from controllers.idempotency_controller import IdempotencyController
from dtos import CreditAdvanceDTO
from errors import (
    AccountNotApproved,
    AccountNotFound,
    BankSlipNotEligible,
    BankSlipNotFound,
)
from repositories import AccountRepository, CreditAdvanceRepository, PricingRepository, RiskPolicyRepository, TransactionRepository
from utils.metrics import observe_lock_wait, record_idempotency_replay
from utils.transient_retry import execute_with_transient_retry


class CreditAdvanceController(BaseController):
    """Antecipação de boletos pendentes, sempre lastreada em recebíveis reais."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.credit_advance_repository = CreditAdvanceRepository(self.context)
        self.transaction_repository = TransactionRepository(self.context)
        self.idempotency_controller = IdempotencyController(self.context)
        self.pricing_repository = PricingRepository(self.context)
        self.risk_policy_repository = RiskPolicyRepository(self.context)

    @classmethod
    def create_with_transient_retry(
        cls, account_key: str, payload: dict, idempotency_key: str
    ) -> tuple[dict, bool]:
        """Recria controller/sessão para cada tentativa transitória completa."""
        return execute_with_transient_retry(
            lambda: cls().create(account_key, payload, idempotency_key)
        )

    def create(self, account_key: str, payload: dict, idempotency_key: str) -> tuple[dict, bool]:
        account = self.account_repository.get_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)

        idempotency = self.idempotency_controller.begin(
            account.id, "credit_advance", idempotency_key, payload
        )
        if idempotency.should_replay:
            record_idempotency_replay("credit_advance")
            return idempotency.response_body, True

        started_at = time.perf_counter()
        account = self.account_repository.get_by_key_for_update(account_key)
        observe_lock_wait("account", time.perf_counter() - started_at)
        if account is None:
            raise AccountNotFound(account_key)
        if account.status.enumerator != "APPROVED":
            raise AccountNotApproved(account_key)

        requested_keys = payload["bank_slip_keys"]
        started_at = time.perf_counter()
        bank_slips = self.credit_advance_repository.get_bank_slips_for_account_for_update(
            account.id, requested_keys
        )
        observe_lock_wait("bank_slips", time.perf_counter() - started_at)
        if len(bank_slips) != len(requested_keys):
            raise BankSlipNotFound()
        if any(
            bank_slip.status.enumerator != "PENDING" or bank_slip.credit_advance_id is not None
            for bank_slip in bank_slips
        ):
            raise BankSlipNotEligible()

        gross_amount = sum(bank_slip.amount for bank_slip in bank_slips)
        risk_snapshot = self.risk_policy_repository.apply_credit_advance(
            account.customer_id, gross_amount, len(bank_slips)
        )
        pricing = self.pricing_repository.resolve(account.customer_id, "CREDIT_ADVANCE", gross_amount)
        fee_amount = pricing.fee_amount
        credit_advance = self.credit_advance_repository.create(account.id, gross_amount, fee_amount)
        credit_advance.pricing_snapshot_id = pricing.id
        credit_advance.risk_policy_snapshot_id = risk_snapshot.id
        for bank_slip in bank_slips:
            bank_slip.credit_advance_id = credit_advance.id

        operation_key = str(uuid4())
        self.transaction_repository.create_entry(
            account, "ADVANCE_CREDIT", gross_amount, operation_key,
            risk_policy_snapshot_id=risk_snapshot.id,
        )
        if fee_amount > 0:
            self.transaction_repository.create_entry(
                account, "ADVANCE_FEE", -fee_amount, operation_key,
                pricing_snapshot_id=pricing.id,
            )

        response = CreditAdvanceDTO.obj_to_created_dict(
            credit_advance, requested_keys, account.balance
        )
        self.idempotency_controller.store_response(idempotency.record, 201, response)
        self.audit.record(
            "CREDIT_ADVANCE_CREATED",
            "CREDIT_ADVANCE",
            credit_advance.credit_advance_key,
            current_summary={
                "account_key": account_key,
                "fee_amount": fee_amount,
                "gross_amount": gross_amount,
                "net_amount": response["net_amount"],
                "pricing_policy_key": pricing.policy_key,
                "pricing_policy_version": pricing.policy_version,
                "risk_policy_key": risk_snapshot.policy_key,
                "risk_policy_version": risk_snapshot.policy_version,
            },
        )
        self.session.commit()
        return response, False
