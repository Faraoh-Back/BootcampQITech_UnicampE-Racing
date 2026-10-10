from tests.utils.request_generator import RequestGenerator
from tests.utils.mock_server import expect_bankslip_ok, reset


def setup_function():
    reset()


def teardown_function():
    reset()


class TestPricingPolicy:
    def test_customer_policy_overrides_default_and_is_versioned_without_repricing_history(
        self, make_customer, make_account
    ):
        preferred_customer = make_customer()["response"]["customer_key"]
        fallback_customer = make_customer()["response"]["customer_key"]
        origin_key = make_account(preferred_customer)["response"]["account_key"]
        preferred_destination = make_account(preferred_customer)["response"]["account_key"]
        fallback_origin = make_account(fallback_customer)["response"]["account_key"]
        fallback_destination = make_account(fallback_customer)["response"]["account_key"]

        status, first_policy = RequestGenerator.POST_pricing_policy({
            "customer_key": preferred_customer,
            "operation": "TRANSFER",
            "fixed_fee_cents": 7,
            "percentage_basis_points": 100,
        })
        assert status == 201
        assert first_policy["version"] == 1

        assert RequestGenerator.POST_transaction(origin_key, {"type": "DEPOSIT", "amount": 1000})[0] == 201
        status, transfer = RequestGenerator.POST_transaction(origin_key, {
            "type": "TRANSFER", "amount": 500,
            "destination_account_key": preferred_destination,
        })
        assert status == 201
        assert transfer["fee_amount"] == 12  # 7 centavos + 1% de 500, sem float.
        assert transfer["balance"] == 488

        status, second_policy = RequestGenerator.POST_pricing_policy({
            "customer_key": preferred_customer,
            "operation": "TRANSFER",
            "fixed_fee_cents": 25,
            "percentage_basis_points": 0,
        })
        assert status == 201
        assert second_policy["version"] == 2
        assert second_policy["policy_key"] != first_policy["policy_key"]

        assert RequestGenerator.POST_transaction(origin_key, {"type": "DEPOSIT", "amount": 100})[0] == 201
        status, later_transfer = RequestGenerator.POST_transaction(origin_key, {
            "type": "TRANSFER", "amount": 100,
            "destination_account_key": preferred_destination,
        })
        assert status == 201
        assert later_transfer["fee_amount"] == 25

        assert RequestGenerator.POST_transaction(fallback_origin, {"type": "DEPOSIT", "amount": 300})[0] == 201
        status, fallback_transfer = RequestGenerator.POST_transaction(fallback_origin, {
            "type": "TRANSFER", "amount": 100,
            "destination_account_key": fallback_destination,
        })
        assert status == 201
        assert fallback_transfer["fee_amount"] == 100

        status, statement = RequestGenerator.GET_transactions(origin_key, {"type": "TRANSFER_FEE", "limit": 10})
        assert status == 200
        assert [entry["amount"] for entry in statement["data"]] == [-25, -12]

        status, audit = RequestGenerator.GET_audit_events()
        assert status == 200
        pricing_events = [event for event in audit["data"] if event["action"] == "PRICING_POLICY_CREATED"]
        assert {event["resource_key"] for event in pricing_events} >= {
            first_policy["policy_key"], second_policy["policy_key"]
        }

    def test_policy_applies_to_billing_issuance_and_credit_advance(self, make_customer, make_account):
        customer_key = make_customer()["response"]["customer_key"]
        account_key = make_account(customer_key)["response"]["account_key"]
        for operation, fixed_fee_cents in (("BANK_SLIP_ISSUANCE", 4), ("CREDIT_ADVANCE", 11)):
            status, _ = RequestGenerator.POST_pricing_policy({
                "customer_key": customer_key,
                "operation": operation,
                "fixed_fee_cents": fixed_fee_cents,
                "percentage_basis_points": 0,
            })
            assert status == 201

        assert RequestGenerator.POST_transaction(account_key, {"type": "DEPOSIT", "amount": 1000})[0] == 201
        expect_bankslip_ok()
        status, plan = RequestGenerator.POST_billing_plan(account_key, {
            "base_amount": 15000, "first_due_date": "2027-01-31",
        })
        assert status == 201
        assert plan["issuance_fee_amount"] == 4

        status, advance = RequestGenerator.POST_credit_advance(account_key, {
            "bank_slip_keys": [plan["bank_slips"][0]["bank_slip_key"]],
        })
        assert status == 201
        assert advance["gross_amount"] == 15000
        assert advance["fee_amount"] == 11
        assert advance["net_amount"] == 14989
