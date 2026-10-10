from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import text

from database import Context
from errors import ProductNotEnabled, RiskLimitExceeded
from models import CustomerDailyOutgoing, RiskPolicy, RiskPolicySnapshot


class RiskPolicyRepository:
    """Resolve e materializa decisões de risco dentro da transação atual."""

    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def resolve(self, customer_id: int) -> RiskPolicy:
        now = datetime.utcnow()
        policy = self.session.query(RiskPolicy).filter(
            RiskPolicy.effective_from <= now,
            (RiskPolicy.effective_until.is_(None) | (RiskPolicy.effective_until > now)),
            (RiskPolicy.customer_id == customer_id) | RiskPolicy.customer_id.is_(None),
        ).order_by(RiskPolicy.customer_id.desc().nulls_last(), RiskPolicy.version.desc()).first()
        if policy is None:
            raise RuntimeError("No active risk policy exists.")
        return policy

    def apply_transfer(self, customer_id: int, amount: int) -> RiskPolicySnapshot:
        policy = self.resolve(customer_id)
        if not policy.transfer_enabled:
            raise ProductNotEnabled("TRANSFER")
        if amount > policy.max_transfer_amount:
            raise RiskLimitExceeded("transfer amount")

        today = date.today()
        # Contas distintas de uma mesma PME compartilham o teto. A advisory
        # lock fecha a corrida antes de existir a primeira linha do dia.
        scope = f"daily-outgoing:{customer_id}:{today.isoformat()}"
        self.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:scope))"), {"scope": scope})
        usage = self.session.query(CustomerDailyOutgoing).filter(
            CustomerDailyOutgoing.customer_id == customer_id,
            CustomerDailyOutgoing.operation_date == today,
        ).with_for_update().first()
        before = usage.consumed_amount if usage is not None else 0
        after = before + amount
        if after > policy.daily_outgoing_limit:
            raise RiskLimitExceeded("daily outgoing amount")
        if usage is None:
            usage = CustomerDailyOutgoing(
                customer_id=customer_id, operation_date=today, consumed_amount=after
            )
            self.session.add(usage)
        else:
            usage.consumed_amount = after
        return self._snapshot(policy, "TRANSFER", amount, 0, before, after)

    def assert_billing_plan_enabled(self, customer_id: int) -> None:
        if not self.resolve(customer_id).billing_plan_enabled:
            raise ProductNotEnabled("BILLING_PLAN")

    def evaluate_transfer(self, customer_id: int, amount: int) -> tuple[RiskPolicy, int]:
        policy = self.resolve(customer_id)
        if not policy.transfer_enabled:
            raise ProductNotEnabled("TRANSFER")
        if amount > policy.max_transfer_amount:
            raise RiskLimitExceeded("transfer amount")
        usage = self.session.query(CustomerDailyOutgoing).filter(
            CustomerDailyOutgoing.customer_id == customer_id,
            CustomerDailyOutgoing.operation_date == date.today(),
        ).first()
        consumed = usage.consumed_amount if usage else 0
        if consumed + amount > policy.daily_outgoing_limit:
            raise RiskLimitExceeded("daily outgoing amount")
        return policy, consumed

    def evaluate_billing_plan(self, customer_id: int) -> RiskPolicy:
        policy = self.resolve(customer_id)
        if not policy.billing_plan_enabled:
            raise ProductNotEnabled("BILLING_PLAN")
        return policy

    def evaluate_credit_advance(self, customer_id: int, amount: int, bank_slips: int) -> RiskPolicy:
        policy = self.resolve(customer_id)
        if not policy.credit_advance_enabled:
            raise ProductNotEnabled("CREDIT_ADVANCE")
        if amount > policy.max_credit_advance_amount:
            raise RiskLimitExceeded("credit advance amount")
        if bank_slips > policy.max_advance_bank_slips:
            raise RiskLimitExceeded("credit advance bank slip count")
        return policy

    def apply_billing_plan(self, customer_id: int, amount: int) -> RiskPolicySnapshot:
        policy = self.resolve(customer_id)
        if not policy.billing_plan_enabled:
            raise ProductNotEnabled("BILLING_PLAN")
        return self._snapshot(policy, "BILLING_PLAN", amount, 0)

    def apply_credit_advance(
        self, customer_id: int, amount: int, bank_slips: int
    ) -> RiskPolicySnapshot:
        policy = self.resolve(customer_id)
        if not policy.credit_advance_enabled:
            raise ProductNotEnabled("CREDIT_ADVANCE")
        if amount > policy.max_credit_advance_amount:
            raise RiskLimitExceeded("credit advance amount")
        if bank_slips > policy.max_advance_bank_slips:
            raise RiskLimitExceeded("credit advance bank slip count")
        return self._snapshot(policy, "CREDIT_ADVANCE", amount, bank_slips)

    def create_policy(self, customer_id: int | None, payload: dict) -> RiskPolicy:
        scope = f"risk-policy:{customer_id if customer_id is not None else 'default'}"
        self.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:scope))"), {"scope": scope})
        now = datetime.utcnow()
        scoped = self.session.query(RiskPolicy).filter(
            RiskPolicy.customer_id.is_(None) if customer_id is None else RiskPolicy.customer_id == customer_id
        )
        latest = scoped.order_by(RiskPolicy.version.desc()).first()
        for active in scoped.filter(RiskPolicy.effective_until.is_(None)).with_for_update().all():
            active.effective_until = now
        policy = RiskPolicy(
            policy_key=str(uuid4()), customer_id=customer_id,
            version=(latest.version if latest else 0) + 1,
            transfer_enabled=payload["transfer_enabled"],
            billing_plan_enabled=payload["billing_plan_enabled"],
            credit_advance_enabled=payload["credit_advance_enabled"],
            max_transfer_amount=payload["max_transfer_amount"],
            daily_outgoing_limit=payload["daily_outgoing_limit"],
            max_credit_advance_amount=payload["max_credit_advance_amount"],
            max_advance_bank_slips=payload["max_advance_bank_slips"],
            effective_from=now,
        )
        self.session.add(policy)
        self.session.flush()
        return policy

    def _snapshot(self, policy, operation, amount, bank_slips, before=None, after=None):
        snapshot = RiskPolicySnapshot(
            policy_key=policy.policy_key, policy_version=policy.version,
            customer_id=policy.customer_id, operation=operation,
            transfer_enabled=policy.transfer_enabled,
            billing_plan_enabled=policy.billing_plan_enabled,
            credit_advance_enabled=policy.credit_advance_enabled,
            max_transfer_amount=policy.max_transfer_amount,
            daily_outgoing_limit=policy.daily_outgoing_limit,
            max_credit_advance_amount=policy.max_credit_advance_amount,
            max_advance_bank_slips=policy.max_advance_bank_slips,
            requested_amount=amount, requested_bank_slips=bank_slips,
            daily_outgoing_before=before, daily_outgoing_after=after,
        )
        self.session.add(snapshot)
        self.session.flush()
        return snapshot
