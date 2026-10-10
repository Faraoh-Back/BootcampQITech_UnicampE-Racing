from datetime import datetime, timedelta
from hashlib import sha256
import json
from uuid import uuid4

from database import Context
from models import Quote


class QuoteRepository:
    TTL_SECONDS = 60

    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, account_id: int, payload: dict, operation: str, gross_amount: int,
               fee_amount: int, pricing_policy, risk_policy) -> Quote:
        request_hash = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        quote = Quote(
            quote_key=str(uuid4()), account_id=account_id, operation=operation,
            request_hash=request_hash, gross_amount=gross_amount, fee_amount=fee_amount,
            net_amount=gross_amount - fee_amount,
            pricing_policy_key=pricing_policy.policy_key, pricing_version=pricing_policy.version,
            risk_policy_key=risk_policy.policy_key, risk_version=risk_policy.version,
            expires_at=datetime.utcnow() + timedelta(seconds=self.TTL_SECONDS),
        )
        self.session.add(quote)
        self.session.flush()
        return quote
