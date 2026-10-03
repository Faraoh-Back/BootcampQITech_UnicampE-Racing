from uuid import uuid4

from constants import ADVANCE_FEE_PERCENT
from controllers.base_controller import BaseController
from controllers.idempotency_controller import IdempotencyController
from dtos import CreditAdvanceDTO
from errors import (
    AccountNotApproved,
    AccountNotFound,
    BankSlipNotEligible,
    BankSlipNotFound,
)
from repositories import AccountRepository, CreditAdvanceRepository, TransactionRepository


class CreditAdvanceController(BaseController):
    """Antecipação de boletos pendentes, sempre lastreada em recebíveis reais."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.credit_advance_repository = CreditAdvanceRepository(self.context)
        self.transaction_repository = TransactionRepository(self.context)
        self.idempotency_controller = IdempotencyController(self.context)

    def create(self, account_key: str, payload: dict, idempotency_key: str) -> tuple[dict, bool]:
        account = self.account_repository.get_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)

        idempotency = self.idempotency_controller.begin(
            account.id, "credit_advance", idempotency_key, payload
        )
        if idempotency.should_replay:
            return idempotency.response_body, True

        account = self.account_repository.get_by_key_for_update(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        if account.status.enumerator != "APPROVED":
            raise AccountNotApproved(account_key)

        requested_keys = payload["bank_slip_keys"]
        bank_slips = self.credit_advance_repository.get_bank_slips_for_account_for_update(
            account.id, requested_keys
        )
        if len(bank_slips) != len(requested_keys):
            raise BankSlipNotFound()
        if any(
            bank_slip.status.enumerator != "PENDING" or bank_slip.credit_advance_id is not None
            for bank_slip in bank_slips
        ):
            raise BankSlipNotEligible()

        gross_amount = sum(bank_slip.amount for bank_slip in bank_slips)
        fee_amount = (gross_amount * ADVANCE_FEE_PERCENT + 50) // 100
        credit_advance = self.credit_advance_repository.create(account.id, gross_amount, fee_amount)
        for bank_slip in bank_slips:
            bank_slip.credit_advance_id = credit_advance.id

        operation_key = str(uuid4())
        self.transaction_repository.create_entry(
            account, "ADVANCE_CREDIT", gross_amount, operation_key
        )
        if fee_amount > 0:
            self.transaction_repository.create_entry(
                account, "ADVANCE_FEE", -fee_amount, operation_key
            )

        response = CreditAdvanceDTO.obj_to_created_dict(
            credit_advance, requested_keys, account.balance
        )
        self.idempotency_controller.store_response(idempotency.record, 201, response)
        self.session.commit()
        return response, False
