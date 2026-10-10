from controllers.base_controller import BaseController
from errors import CustomerNotFound, InvalidSchema
from repositories import CustomerRepository, RiskPolicyRepository


class RiskPolicyController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.customer_repository = CustomerRepository(self.context)
        self.risk_policy_repository = RiskPolicyRepository(self.context)

    def create(self, payload: dict) -> dict:
        integer_fields = (
            "max_transfer_amount", "daily_outgoing_limit",
            "max_credit_advance_amount", "max_advance_bank_slips",
        )
        if any(type(payload[field]) is not int for field in integer_fields):
            raise InvalidSchema("Risk limits must be integer amounts in cents or an integer count.")
        customer_key = payload.get("customer_key")
        customer_id = None
        if customer_key is not None:
            customer = self.customer_repository.get_by_key(customer_key)
            if customer is None:
                raise CustomerNotFound(customer_key)
            customer_id = customer.id
        policy = self.risk_policy_repository.create_policy(customer_id, payload)
        self.audit.record(
            "RISK_POLICY_CREATED", "RISK_POLICY", policy.policy_key,
            current_summary={
                "customer_key": customer_key, "version": policy.version,
                "transfer_enabled": policy.transfer_enabled,
                "billing_plan_enabled": policy.billing_plan_enabled,
                "credit_advance_enabled": policy.credit_advance_enabled,
                "max_transfer_amount": policy.max_transfer_amount,
                "daily_outgoing_limit": policy.daily_outgoing_limit,
                "max_credit_advance_amount": policy.max_credit_advance_amount,
                "max_advance_bank_slips": policy.max_advance_bank_slips,
            },
        )
        self.session.commit()
        return {
            "policy_key": policy.policy_key, "customer_key": customer_key,
            "version": policy.version, "transfer_enabled": policy.transfer_enabled,
            "billing_plan_enabled": policy.billing_plan_enabled,
            "credit_advance_enabled": policy.credit_advance_enabled,
            "max_transfer_amount": policy.max_transfer_amount,
            "daily_outgoing_limit": policy.daily_outgoing_limit,
            "max_credit_advance_amount": policy.max_credit_advance_amount,
            "max_advance_bank_slips": policy.max_advance_bank_slips,
            "effective_from": policy.effective_from.isoformat(),
        }
