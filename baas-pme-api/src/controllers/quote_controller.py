from controllers.base_controller import BaseController
from errors import AccountNotFound, BankSlipNotEligible, BankSlipNotFound, InvalidSchema
from repositories import AccountRepository, CreditAdvanceRepository, PricingRepository, QuoteRepository, RiskPolicyRepository


class QuoteController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.credit_advance_repository = CreditAdvanceRepository(self.context)
        self.pricing_repository = PricingRepository(self.context)
        self.risk_policy_repository = RiskPolicyRepository(self.context)
        self.quote_repository = QuoteRepository(self.context)

    def create(self, account_key: str, payload: dict) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        operation = payload["operation"]
        if operation == "TRANSFER":
            gross = self._amount(payload)
            pricing = self.pricing_repository.get_policy(account.customer_id, "TRANSFER")
            risk, consumed = self.risk_policy_repository.evaluate_transfer(account.customer_id, gross)
            extras = {"daily_outgoing_consumed": consumed, "daily_outgoing_remaining": risk.daily_outgoing_limit - consumed}
        elif operation == "BILLING_PLAN":
            gross = self._amount(payload) * 12
            pricing = self.pricing_repository.get_policy(account.customer_id, "BANK_SLIP_ISSUANCE")
            risk = self.risk_policy_repository.evaluate_billing_plan(account.customer_id)
            extras = {"installments_count": 12}
        else:
            keys = payload.get("bank_slip_keys")
            if not keys:
                raise InvalidSchema("bank_slip_keys is required for CREDIT_ADVANCE quote.")
            bank_slips = self.credit_advance_repository.get_bank_slips_for_account(account.id, keys)
            if len(bank_slips) != len(keys):
                raise BankSlipNotFound()
            if any(s.status.enumerator != "PENDING" or s.credit_advance_id is not None for s in bank_slips):
                raise BankSlipNotEligible()
            gross = sum(s.amount for s in bank_slips)
            pricing = self.pricing_repository.get_policy(account.customer_id, "CREDIT_ADVANCE")
            risk = self.risk_policy_repository.evaluate_credit_advance(account.customer_id, gross, len(keys))
            extras = {"bank_slips_count": len(keys)}
        fee = self.pricing_repository.calculate_fee(pricing, gross)
        quote = self.quote_repository.create(account.id, payload, operation, gross, fee, pricing, risk)
        self.audit.record("QUOTE_CREATED", "QUOTE", quote.quote_key, current_summary={
            "account_key": account_key, "operation": operation, "gross_amount": gross,
            "fee_amount": fee, "pricing_policy_key": pricing.policy_key,
            "pricing_policy_version": pricing.version, "risk_policy_key": risk.policy_key,
            "risk_policy_version": risk.version, "expires_at": quote.expires_at.isoformat(),
        })
        self.session.commit()
        return {
            "quote_key": quote.quote_key, "operation": operation, "gross_amount": gross,
            "fee_amount": fee, "net_amount": quote.net_amount,
            "pricing_policy_key": pricing.policy_key, "pricing_policy_version": pricing.version,
            "risk_policy_key": risk.policy_key, "risk_policy_version": risk.version,
            "expires_at": quote.expires_at.isoformat(), "informative": True, **extras,
        }

    @staticmethod
    def _amount(payload: dict) -> int:
        amount = payload.get("amount")
        if type(amount) is not int:
            raise InvalidSchema("amount is required and must be an integer amount in cents.")
        return amount
