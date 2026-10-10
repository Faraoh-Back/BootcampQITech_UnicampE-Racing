from tests.utils.request_generator import RequestGenerator


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
