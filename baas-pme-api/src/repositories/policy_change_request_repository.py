from datetime import datetime
from uuid import uuid4

from database import Context
from models import PolicyChangeRequest


class PolicyChangeRequestRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, customer_id, policy_type, payload, creator_user_id):
        item = PolicyChangeRequest(request_key=str(uuid4()), customer_id=customer_id,
            policy_type=policy_type, payload=payload, status="DRAFT", creator_user_id=creator_user_id)
        self.session.add(item)
        self.session.flush()
        return item

    def get_for_update(self, request_key):
        return self.session.query(PolicyChangeRequest).filter(
            PolicyChangeRequest.request_key == request_key
        ).with_for_update().first()

    @staticmethod
    def submit(item):
        item.status = "PENDING_APPROVAL"
        item.submitted_at = datetime.utcnow()

    @staticmethod
    def approve(item, approver_user_id, policy_key):
        item.status = "ACTIVE"
        item.approver_user_id = approver_user_id
        item.published_policy_key = policy_key
        item.approved_at = datetime.utcnow()
