from controllers.base_controller import BaseController
from errors import CustomerNotFound, InvalidSchema
from repositories import CustomerRepository, PricingRepository


class PricingPolicyController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.customer_repository = CustomerRepository(self.context)
        self.pricing_repository = PricingRepository(self.context)

    def create(self, payload: dict) -> dict:
        if type(payload["fixed_fee_cents"]) is not int or type(payload["percentage_basis_points"]) is not int:
            raise InvalidSchema("Pricing values must be integer cents and integer basis points.")
        customer_id = None
        customer_key = payload.get("customer_key")
        if customer_key is not None:
            customer = self.customer_repository.get_by_key(customer_key)
            if customer is None:
                raise CustomerNotFound(customer_key)
            customer_id = customer.id
        policy = self.pricing_repository.create_policy(
            customer_id, payload["operation"], payload["fixed_fee_cents"],
            payload["percentage_basis_points"]
        )
        self.audit.record("PRICING_POLICY_CREATED", "PRICING_POLICY", policy.policy_key,
            current_summary={"customer_key": customer_key, "operation": policy.operation,
                             "version": policy.version, "fixed_fee_cents": policy.fixed_fee_cents,
                             "percentage_basis_points": policy.percentage_basis_points})
        self.session.commit()
        return {"policy_key": policy.policy_key, "customer_key": customer_key,
                "operation": policy.operation, "version": policy.version,
                "fixed_fee_cents": policy.fixed_fee_cents,
                "percentage_basis_points": policy.percentage_basis_points,
                "effective_from": policy.effective_from.isoformat()}

