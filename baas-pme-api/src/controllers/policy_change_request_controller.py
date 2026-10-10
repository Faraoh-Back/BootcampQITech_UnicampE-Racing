from controllers.auth_controller import AuthController
from controllers.base_controller import BaseController
from errors import AccountAccessForbidden, CustomerNotFound, MakerCheckerViolation, PolicyChangeRequestNotFound
from repositories import CustomerRepository, PolicyChangeRequestRepository, PricingRepository, RiskPolicyRepository, UserRepository
from utils.request_context import set_audit_actor


class PolicyChangeRequestController(BaseController):
    def __init__(self):
        super().__init__(__name__)
        self.customers = CustomerRepository(self.context)
        self.users = UserRepository(self.context)
        self.requests = PolicyChangeRequestRepository(self.context)
        self.pricing = PricingRepository(self.context)
        self.risk = RiskPolicyRepository(self.context)

    def create(self, payload, authorization):
        customer = self.customers.get_by_key(payload["customer_key"])
        if customer is None: raise CustomerNotFound(payload["customer_key"])
        user = self._owner(customer.id, authorization)
        item = self.requests.create(customer.id, payload["policy_type"], payload["policy"], user.id)
        self.audit.record("POLICY_CHANGE_DRAFTED", "POLICY_CHANGE_REQUEST", item.request_key,
            current_summary={"policy_type": item.policy_type, "customer_key": customer.customer_key, "status": item.status})
        self.session.commit()
        return self._dto(item)

    def submit(self, request_key, authorization):
        item = self.requests.get_for_update(request_key)
        if item is None: raise PolicyChangeRequestNotFound()
        user = self._owner(item.customer_id, authorization)
        if item.creator_user_id != user.id or item.status != "DRAFT": raise MakerCheckerViolation("Only the creator can submit a draft policy request.")
        self.requests.submit(item)
        self.audit.record("POLICY_CHANGE_SUBMITTED", "POLICY_CHANGE_REQUEST", item.request_key,
            current_summary={"status": item.status})
        self.session.commit()
        return self._dto(item)

    def approve(self, request_key, authorization):
        item = self.requests.get_for_update(request_key)
        if item is None: raise PolicyChangeRequestNotFound()
        user = self._owner(item.customer_id, authorization)
        if item.status != "PENDING_APPROVAL" or item.creator_user_id == user.id: raise MakerCheckerViolation()
        if item.policy_type == "PRICING":
            policy = self.pricing.create_policy(item.customer_id, **item.payload)
        else:
            policy = self.risk.create_policy(item.customer_id, item.payload)
        self.requests.approve(item, user.id, policy.policy_key)
        self.audit.record("POLICY_CHANGE_APPROVED", "POLICY_CHANGE_REQUEST", item.request_key,
            current_summary={"status": item.status, "published_policy_key": policy.policy_key, "policy_type": item.policy_type})
        self.session.commit()
        return self._dto(item)

    def _owner(self, customer_id, authorization):
        claims = AuthController()._claims_for_active_session(authorization)
        session = self.users.get_active_session_by_key_for_user(claims["sid"], claims["sub"])
        if session is None or self.users.get_customer_role(session.user_id, customer_id) != "OWNER": raise AccountAccessForbidden()
        set_audit_actor("USER", claims["sub"])
        return session.user

    @staticmethod
    def _dto(item):
        return {"request_key": item.request_key, "policy_type": item.policy_type, "status": item.status,
                "published_policy_key": item.published_policy_key, "submitted_at": item.submitted_at.isoformat() if item.submitted_at else None,
                "approved_at": item.approved_at.isoformat() if item.approved_at else None}
