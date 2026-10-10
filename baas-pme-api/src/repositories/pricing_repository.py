from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from sqlalchemy import text

from database import Context
from models import PricingPolicy, PricingSnapshot


class PricingRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def resolve(self, customer_id: int, operation: str, base_amount: int) -> PricingSnapshot:
        policy = self.get_policy(customer_id, operation)
        fee_amount = self.calculate_fee(policy, base_amount)
        return self.create_snapshot(policy, base_amount, fee_amount)

    def create_snapshot(
        self, policy: PricingPolicy, base_amount: int, fee_amount: int
    ) -> PricingSnapshot:
        """Persiste a escolha já calculada, sem resolver outra versão de preço."""
        snapshot = PricingSnapshot(policy_key=policy.policy_key, policy_version=policy.version,
            customer_id=policy.customer_id, operation=policy.operation, fixed_fee_cents=policy.fixed_fee_cents,
            percentage_basis_points=policy.percentage_basis_points, base_amount=base_amount,
            fee_amount=fee_amount)
        self.session.add(snapshot)
        self.session.flush()
        return snapshot

    def get_policy(self, customer_id: int, operation: str) -> PricingPolicy:
        now = datetime.utcnow()
        policies = self.session.query(PricingPolicy).filter(
            PricingPolicy.operation == operation,
            PricingPolicy.effective_from <= now,
            (PricingPolicy.effective_until.is_(None) | (PricingPolicy.effective_until > now)),
            (PricingPolicy.customer_id == customer_id) | PricingPolicy.customer_id.is_(None),
        ).order_by(PricingPolicy.customer_id.desc().nulls_last(), PricingPolicy.version.desc()).all()
        if not policies:
            raise RuntimeError(f"No active pricing policy for {operation}.")
        return policies[0]

    @staticmethod
    def calculate_fee(policy: PricingPolicy, base_amount: int) -> int:
        variable = int((Decimal(base_amount) * Decimal(policy.percentage_basis_points) / Decimal(10000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return policy.fixed_fee_cents + variable

    def create_policy(self, customer_id, operation, fixed_fee_cents, percentage_basis_points):
        """Publica nova versão sem alterar seus termos econômicos anteriores."""
        now = datetime.utcnow()
        # Serializa também a primeira política de uma PME, quando ainda não
        # existe linha para travar com FOR UPDATE.
        scope = f"pricing:{customer_id if customer_id is not None else 'default'}:{operation}"
        self.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:scope))"), {"scope": scope})
        query = self.session.query(PricingPolicy.version).filter(PricingPolicy.operation == operation)
        query = query.filter(PricingPolicy.customer_id.is_(None) if customer_id is None else PricingPolicy.customer_id == customer_id)
        latest = query.order_by(PricingPolicy.version.desc()).first()
        active_policies = self.session.query(PricingPolicy).filter(
            PricingPolicy.operation == operation,
            PricingPolicy.effective_until.is_(None),
            PricingPolicy.customer_id.is_(None) if customer_id is None else PricingPolicy.customer_id == customer_id,
        ).with_for_update().all()
        for active_policy in active_policies:
            active_policy.effective_until = now
        policy = PricingPolicy(policy_key=str(uuid4()), customer_id=customer_id, operation=operation,
            version=(latest[0] if latest else 0) + 1, fixed_fee_cents=fixed_fee_cents,
            percentage_basis_points=percentage_basis_points, effective_from=now)
        self.session.add(policy)
        self.session.flush()
        return policy

