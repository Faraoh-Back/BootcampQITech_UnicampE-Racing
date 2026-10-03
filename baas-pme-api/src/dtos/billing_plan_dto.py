from models import BankSlip, BillingPlan


class BillingPlanDTO:
    @staticmethod
    def obj_to_created_dict(plan: BillingPlan) -> dict:
        return {
            "plan_key": plan.plan_key,
            "account_key": plan.account.account_key,
            "base_amount": plan.base_amount,
            "installments_count": len(plan.bank_slips),
            "bank_slips": [BillingPlanDTO._bank_slip_to_dict(slip) for slip in plan.bank_slips],
            "created_at": plan.created_at.isoformat(),
        }

    @staticmethod
    def obj_to_dict(plan: BillingPlan) -> dict:
        return {
            "plan_key": plan.plan_key,
            "account_key": plan.account.account_key,
            "base_amount": plan.base_amount,
            "first_due_date": plan.first_due_date.isoformat(),
            "created_at": plan.created_at.isoformat(),
            "bank_slips": [
                BillingPlanDTO._bank_slip_to_dict(slip, include_events=True)
                for slip in plan.bank_slips
            ],
        }

    @staticmethod
    def _bank_slip_to_dict(bank_slip: BankSlip, include_events: bool = False) -> dict:
        result = {
            "bank_slip_key": bank_slip.bank_slip_key,
            "installment_number": bank_slip.installment_number,
            "amount": bank_slip.amount,
            "due_date": bank_slip.due_date.isoformat(),
            "barcode": bank_slip.barcode,
            "status": bank_slip.status.enumerator,
        }
        if include_events:
            result["batch_number"] = bank_slip.batch_number
            result["adjustment_rate"] = (
                format(bank_slip.adjustment_rate.normalize(), "f")
                if bank_slip.adjustment_rate is not None
                else None
            )
            result["status_events"] = [
                {
                    "status": event.status.enumerator,
                    "event_datetime": event.event_datetime.isoformat(),
                }
                for event in bank_slip.status_events
            ]
        if bank_slip.credit_advance is not None:
            result["credit_advance_key"] = bank_slip.credit_advance.credit_advance_key
        return result
